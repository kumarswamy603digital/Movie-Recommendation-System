"""Generate concise, honest explanations for each recommendation.

Rules are strict: never invent a reason that isn't supported by data. Every
sentence references a real signal (component score, shared genre, similar-user
overlap) or explicitly says the reason is unavailable.
"""
from __future__ import annotations

import pandas as pd

from app.recommender.base import Scored
from app.recommender.collaborative import CollaborativeRecommender
from app.recommender.content_based import ContentBasedRecommender


def _fmt(v: float) -> str:
    return f"{v:.2f}"


def explain(
    scored: Scored,
    catalogue_row: pd.Series,
    user_seed_movie_ids: list[int] | None,
    content: ContentBasedRecommender | None,
    cf: CollaborativeRecommender | None,
    user_id: int | None = None,
) -> list[str]:
    """Return human-readable reason strings for one recommended movie."""
    reasons: list[str] = []
    comps = scored.components or {}
    genres = str(catalogue_row.get("genres", "") or "").split("|")
    genres = [g.strip() for g in genres if g.strip()]

    # Content signal.
    if content is not None and content.is_ready() and user_seed_movie_ids:
        sim = content.profile_similarity(scored.movie_id, user_seed_movie_ids)
        if sim is not None and sim > 0.05:
            # Which of the user's seed genres overlaps with this movie's genres?
            shared: set[str] = set()
            for sid in user_seed_movie_ids:
                if content._idx.index.get(int(sid)) is None:
                    continue
                # We cannot fetch seed genre without the catalogue; caller has
                # already filtered by preference via `seed_movie_ids`, so a
                # generic-but-honest statement is safe here.
                pass
            reasons.append(
                f"Similar to movies you rated (content similarity ≈ {_fmt(sim)})."
            )
            if genres:
                reasons.append("Genres: " + ", ".join(genres[:4]))

    # Collaborative signal.
    if cf is not None and cf.is_ready() and comps.get("collaborative", 0) > 0:
        reasons.append("Users with similar rating history also rated this highly.")

    # Popularity signal.
    if comps.get("popularity", 0) > 0.4:
        reasons.append("Well-rated and popular in the MovieLens dataset.")

    # Cold-start / fallback.
    if not reasons:
        reasons.append("Broad popularity fallback (no personal signal available yet).")

    return reasons


def personalized_flag(user_id: int | None, cf: CollaborativeRecommender | None) -> bool:
    """True only if there is genuine personalized evidence for this user."""
    if user_id is None:
        return False
    if cf is not None and cf.is_ready():
        return cf.user_has_history(user_id)
    return False
