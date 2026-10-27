"""Hybrid recommender: weighted blend of normalized component scores.

Design goals:
- Deterministic for the same inputs (stable argsort, explicit tie-breakers).
- Component-score transparency (each item reports its per-component
  contributions so the API can show honest explanations).
- Graceful degradation: any unavailable component is simply skipped and its
  weight is redistributed to the remaining components.
- Cold start: falls through to popularity when the user has no history.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.recommender.base import Recommender, Scored, coerce_movie_ids, normalize_scores
from app.recommender.collaborative import CollaborativeRecommender
from app.recommender.content_based import ContentBasedRecommender
from app.recommender.popularity import PopularityRecommender


@dataclass
class HybridWeights:
    popularity: float = 0.20
    content: float = 0.35
    collaborative: float = 0.45

    def renormalized(self) -> "HybridWeights":
        s = self.popularity + self.content + self.collaborative
        if s <= 0:
            return HybridWeights(1 / 3, 1 / 3, 1 / 3)
        return HybridWeights(self.popularity / s, self.content / s, self.collaborative / s)


class HybridRecommender(Recommender):
    name = "hybrid"

    def __init__(
        self,
        popularity: PopularityRecommender,
        content: ContentBasedRecommender,
        collaborative: CollaborativeRecommender,
        weights: HybridWeights | None = None,
    ) -> None:
        self.pop = popularity
        self.content = content
        self.cf = collaborative
        self.weights = (weights or HybridWeights()).renormalized()

    def is_ready(self) -> bool:
        return any([self.pop.is_ready(), self.content.is_ready(), self.cf.is_ready()])

    def _content_from_profile(
        self, seed_movie_ids: list[int], candidate_ids: np.ndarray, movie_index: dict[int, int]
    ) -> np.ndarray:
        """Content score for each candidate = mean cosine similarity to seeds."""
        if not self.content.is_ready() or not seed_movie_ids:
            return np.zeros(candidate_ids.size)
        idx = self.content._idx
        rows = [idx.index[int(s)] for s in seed_movie_ids if int(s) in idx.index]
        if not rows:
            return np.zeros(candidate_ids.size)
        # Build a profile vector by averaging normalized rows.
        profile = np.zeros(idx.tfidf.shape[1])
        for r in rows:
            profile += np.asarray(idx.tfidf[r].todense()).ravel()
        profile /= max(len(rows), 1)
        # Cosine with each candidate (candidates share the same movie_ids as content index)
        from sklearn.metrics.pairwise import cosine_similarity
        sims = cosine_similarity(profile.reshape(1, -1), idx.tfidf).ravel()
        # Map content rows -> candidate array positions.
        out = np.zeros(candidate_ids.size)
        for i, mid in enumerate(candidate_ids):
            r = idx.index.get(int(mid))
            if r is not None:
                out[i] = sims[r]
        return out

    def rank(
        self,
        user_id: int | None,
        ratings_by_user: pd.Series | None,
        exclude_movie_ids: set[int] | None,
        top_k: int,
        seed_movie_ids: list[int] | None = None,
    ) -> list[Scored]:
        ex = coerce_movie_ids(exclude_movie_ids)

        # Union of every movie we know about.
        all_ids: set[int] = set()
        if self.pop.is_ready():
            all_ids |= self.pop.all_movie_ids()
        if self.content.is_ready():
            all_ids |= {int(x) for x in self.content._idx.movie_ids}
        if self.cf.is_ready():
            all_ids |= {int(x) for x in self.cf._st.movie_ids}
        all_ids -= ex
        if not all_ids:
            return []
        candidate_ids = np.array(sorted(all_ids), dtype=np.int64)

        # Component scores (raw scale, will be normalized together).
        pop_scores = np.zeros(candidate_ids.size)
        if self.pop.is_ready():
            tbl = self.pop._table
            for i, mid in enumerate(candidate_ids):
                r = tbl.index.get(int(mid))
                if r is not None:
                    pop_scores[i] = float(tbl.scores[r])

        content_scores = self._content_from_profile(
            seed_movie_ids or [], candidate_ids, {}
        ) if seed_movie_ids else np.zeros(candidate_ids.size)

        cf_scores = np.zeros(candidate_ids.size)
        cf_map: dict[int, float] = {}
        if self.cf.is_ready() and self.cf.user_has_history(user_id or -1):
            # Ask CF for a longer list so we cover the candidate set.
            cf_list = self.cf.top_for_user(user_id, ratings_by_user, ex, top_k=max(200, top_k * 5))
            cf_map = {s.movie_id: s.score for s in cf_list}
        for i, mid in enumerate(candidate_ids):
            cf_scores[i] = cf_map.get(int(mid), 0.0)

        # Normalize each component independently (min-max on non-zero values).
        pop_n = normalize_scores(pop_scores)
        con_n = normalize_scores(content_scores)
        cf_n = normalize_scores(cf_scores)

        # Weights: drop any component that produced nothing.
        w = self.weights
        active = []
        if np.any(pop_n > 0):
            active.append(("popularity", w.popularity, pop_n))
        if np.any(con_n > 0):
            active.append(("content", w.content, con_n))
        if np.any(cf_n > 0):
            active.append(("collaborative", w.collaborative, cf_n))
        if not active:
            # Fallback to global popularity.
            return self.pop.global_top(top_k=top_k, exclude_movie_ids=ex)

        total_w = sum(a[1] for a in active)
        blended = np.zeros(candidate_ids.size)
        for _, ww, arr in active:
            blended += (ww / total_w) * arr

        # Deterministic order: score DESC, then movie_id ASC for ties.
        order = np.lexsort((candidate_ids, -blended))[:top_k]
        out: list[Scored] = []
        for i in order:
            s = float(blended[i])
            if s <= 0:
                continue
            comps = {
                "popularity": float(pop_n[i]),
                "content": float(con_n[i]),
                "collaborative": float(cf_n[i]),
            }
            out.append(Scored(movie_id=int(candidate_ids[i]), score=s, components=comps))
        return out

    def top_for_user(
        self,
        user_id: int,
        ratings_by_user: pd.Series | None,
        exclude_movie_ids: set[int],
        top_k: int,
    ) -> list[Scored]:
        seed_movie_ids = None
        if ratings_by_user is not None and not ratings_by_user.empty:
            # Prefer highly-rated items as content seeds.
            top = ratings_by_user.sort_values(ascending=False).head(10)
            seed_movie_ids = [int(x) for x in top.index]
        return self.rank(
            user_id=user_id,
            ratings_by_user=ratings_by_user,
            exclude_movie_ids=exclude_movie_ids,
            top_k=top_k,
            seed_movie_ids=seed_movie_ids,
        )
