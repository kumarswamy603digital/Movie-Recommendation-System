"""Re-export ORM models so `from app import models` triggers table registration."""
from app.models.db_models import (  # noqa: F401
    Favorite,
    Preference,
    Rating,
    RecommendationFeedback,
    User,
)

__all__ = [
    "User",
    "Rating",
    "Favorite",
    "Preference",
    "RecommendationFeedback",
]
