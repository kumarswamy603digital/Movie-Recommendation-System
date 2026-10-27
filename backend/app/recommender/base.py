"""Common recommender interface + tiny shared helpers.

Every recommender consumes preprocessed data loaded by `registry.py`. The
interface is intentionally minimal: subclasses implement `top_for_user` and/or
`similar_to_movie` depending on their capability.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Scored:
    """A single scored movie id, before joining with catalogue metadata."""
    movie_id: int
    score: float
    components: dict[str, float] = field(default_factory=dict)


class Recommender(ABC):
    """Base class. Subclasses MUST be safe to call after `is_ready()==True`."""

    name: str = "base"

    @abstractmethod
    def is_ready(self) -> bool:
        ...

    def top_for_user(
        self,
        user_id: int,
        ratings_by_user: pd.Series | None,
        exclude_movie_ids: set[int],
        top_k: int,
    ) -> list[Scored]:
        """Return top-k unseen recommendations for a user.

        Default implementation returns an empty list; concrete recommenders may
        override. `ratings_by_user` is a Series indexed by movie_id with float
        rating values (or None if user is cold-start)."""
        return []

    def similar_to_movie(
        self, movie_id: int, exclude_movie_ids: set[int], top_k: int
    ) -> list[Scored]:
        """Return top-k similar movies. Not all strategies support this."""
        return []


def normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Min-max normalize a 1-D array into [0, 1]. Zero-variance -> all 0.5."""
    if scores.size == 0:
        return scores
    lo, hi = float(scores.min()), float(scores.max())
    if hi - lo < 1e-12:
        return np.full_like(scores, 0.5, dtype=float)
    return (scores - lo) / (hi - lo)


def coerce_movie_ids(x) -> set[int]:
    if x is None:
        return set()
    return {int(v) for v in x if v is not None}
