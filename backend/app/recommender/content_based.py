"""Content-based recommender using TF-IDF over genres (+ title tokens)
and cosine similarity.

Design notes:
- Feature text = "genre|genre genre genre title_tokens"
- L2-normalized TF-IDF matrix (sparse CSR). Similarity = dot product of two
  normalized rows. We use sklearn's cosine_similarity, which handles the
  sparse case efficiently.
- No dense NxN similarity matrix is stored; we compute per-query row * global
  matrix product. This scales to millions of items if needed.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.recommender.base import Recommender, Scored, coerce_movie_ids


def _build_doc(row: pd.Series) -> str:
    genres = str(row.get("genres", "") or "")
    genres_clean = genres.replace("|", " ").lower()
    title = str(row.get("title", "") or "")
    # Strip " (YYYY)" suffix if present (MovieLens style).
    year_idx = title.rfind("(")
    if year_idx > 0 and title.endswith(")"):
        title = title[:year_idx]
    return f"{genres_clean} {title.strip().lower()}"


@dataclass
class ContentIndex:
    movie_ids: np.ndarray            # (N,) int64
    index: dict[int, int]            # movie_id -> row
    tfidf: sparse.csr_matrix         # (N, vocab) L2-normalized
    vectorizer: TfidfVectorizer


class ContentBasedRecommender(Recommender):
    name = "content"

    def __init__(self, index: ContentIndex | None = None) -> None:
        self._idx = index

    @classmethod
    def fit(cls, movies: pd.DataFrame) -> "ContentBasedRecommender":
        """`movies` must have columns: movie_id, title, genres."""
        if movies.empty:
            return cls()
        docs = movies.apply(_build_doc, axis=1).tolist()
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            token_pattern=r"[a-z0-9][a-z0-9\-]+",
            max_features=5000,
        )
        tfidf = vectorizer.fit_transform(docs).tocsr()
        movie_ids = movies["movie_id"].to_numpy(dtype=np.int64)
        index = {int(mid): i for i, mid in enumerate(movie_ids)}
        return cls(ContentIndex(movie_ids=movie_ids, index=index, tfidf=tfidf, vectorizer=vectorizer))

    def save(self, path: str) -> None:
        import joblib
        joblib.dump(self._idx, path)

    @classmethod
    def load(cls, path: str) -> "ContentBasedRecommender":
        import joblib
        return ContentBasedRecommender(index=joblib.load(path))

    def is_ready(self) -> bool:
        return self._idx is not None and self._idx.movie_ids.size > 0

    def similar_to_movie(
        self, movie_id: int, exclude_movie_ids: set[int] | None = None, top_k: int = 20
    ) -> list[Scored]:
        if not self.is_ready():
            return []
        idx = self._idx
        row = idx.index.get(int(movie_id))
        if row is None:
            return []
        ex = coerce_movie_ids(exclude_movie_ids) | {int(movie_id)}
        sims = cosine_similarity(idx.tfidf[row : row + 1], idx.tfidf).ravel()
        # Zero out excluded rows and the movie itself.
        for mid in ex:
            r = idx.index.get(mid)
            if r is not None:
                sims[r] = -1.0
        order = np.argsort(-sims, kind="stable")[:top_k]
        out: list[Scored] = []
        for r in order:
            s = float(sims[r])
            if s <= 0.0:
                continue
            out.append(Scored(movie_id=int(idx.movie_ids[r]), score=s, components={"content": s}))
        return out

    def profile_similarity(
        self, movie_id: int, seed_movie_ids: list[int]
    ) -> float | None:
        """Average cosine similarity between `movie_id` and a set of seed movies."""
        if not self.is_ready():
            return None
        idx = self._idx
        r = idx.index.get(int(movie_id))
        if r is None:
            return None
        seed_rows = [idx.index[int(s)] for s in seed_movie_ids if int(s) in idx.index]
        if not seed_rows:
            return None
        sims = cosine_similarity(idx.tfidf[r : r + 1], idx.tfidf[seed_rows]).ravel()
        return float(sims.mean())
