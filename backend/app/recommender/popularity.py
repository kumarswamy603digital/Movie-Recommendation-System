"""Popularity recommender with Bayesian weighted rating.

Score formula (also known as IMDb Top 250 weighted rating):

    WR = (v / (v + m)) * R + (m / (v + m)) * C

where
- v = number of ratings for the movie
- R = mean rating for the movie
- C = mean rating across the whole catalogue
- m = configurability threshold (equivalent to minimum-ratings filter)

Higher `m` -> stronger pull towards the global mean, so a 5.0 with 3 votes
loses to a 4.3 with 500 votes. This is exactly what we want for a fair
"most popular / best liked" ranking.

Also serves as the cold-start fallback for every other strategy.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.recommender.base import Recommender, Scored, coerce_movie_ids


@dataclass
class PopularityTable:
    movie_ids: np.ndarray          # (N,)
    scores: np.ndarray             # (N,) Bayesian weighted rating
    rating_counts: np.ndarray      # (N,)
    mean_ratings: np.ndarray       # (N,)
    index: dict[int, int]          # movie_id -> row index


class PopularityRecommender(Recommender):
    name = "popularity"

    def __init__(self, table: PopularityTable | None = None) -> None:
        self._table = table

    # -------- lifecycle --------

    @classmethod
    def fit(
        cls,
        ratings: pd.DataFrame,
        min_ratings: int = 20,
        prior_weight: float | None = None,
    ) -> "PopularityRecommender":
        """Build the ranking table from a ratings DataFrame.

        Columns expected: ``movie_id`` (int), ``rating`` (float 1..5).
        ``prior_weight`` is the Bayesian smoothing strength. When None we use
        ``min_ratings * 2`` which is a reasonable default tied to the
        minimum-support threshold.
        """
        grouped = ratings.groupby("movie_id", sort=True)["rating"].agg(["mean", "count"])
        grouped = grouped.rename(columns={"mean": "R", "count": "v"})
        C = float(grouped["R"].mean())
        m = float(prior_weight if prior_weight is not None else max(min_ratings, 1) * 2)

        v = grouped["v"].to_numpy(dtype=np.float64)
        R = grouped["R"].to_numpy(dtype=np.float64)
        wr = (v / (v + m)) * R + (m / (v + m)) * C
        # Suppress very sparse items entirely (they remain retrievable but at bottom).
        wr[v < min_ratings] = 0.0

        movie_ids = grouped.index.to_numpy(dtype=np.int64)
        index = {int(mid): i for i, mid in enumerate(movie_ids)}
        table = PopularityTable(
            movie_ids=movie_ids,
            scores=wr,
            rating_counts=v.astype(np.int64),
            mean_ratings=R,
            index=index,
        )
        return cls(table=table)

    def load(cls, path: str) -> "PopularityRecommender":  # type: ignore[misc]
        import joblib
        return PopularityRecommender(table=joblib.load(path))

    def save(self, path: str) -> None:
        import joblib
        joblib.dump(self._table, path)

    def is_ready(self) -> bool:
        return self._table is not None and self._table.movie_ids.size > 0

    # -------- queries --------

    def global_top(self, top_k: int = 20, exclude_movie_ids: set[int] | None = None) -> list[Scored]:
        if not self.is_ready():
            return []
        ex = coerce_movie_ids(exclude_movie_ids)
        tbl = self._table
        order = np.argsort(-tbl.scores, kind="stable")
        out: list[Scored] = []
        for row in order:
            mid = int(tbl.movie_ids[row])
            if mid in ex:
                continue
            out.append(Scored(movie_id=mid, score=float(tbl.scores[row])))
            if len(out) >= top_k:
                break
        return out

    def top_for_user(
        self,
        user_id: int,
        ratings_by_user: pd.Series | None,
        exclude_movie_ids: set[int],
        top_k: int,
    ) -> list[Scored]:
        # Popularity is not personalized; used as fallback.
        return self.global_top(top_k=top_k, exclude_movie_ids=exclude_movie_ids)

    def stats(self, movie_id: int) -> dict[str, float] | None:
        if not self.is_ready():
            return None
        idx = self._table.index.get(int(movie_id))
        if idx is None:
            return None
        return {
            "mean_rating": float(self._table.mean_ratings[idx]),
            "rating_count": int(self._table.rating_counts[idx]),
            "score": float(self._table.scores[idx]),
        }

    def all_movie_ids(self) -> set[int]:
        if not self.is_ready():
            return set()
        return {int(x) for x in self._table.movie_ids}
