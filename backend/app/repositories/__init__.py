"""Repositories re-export for convenience."""
from app.repositories.repository import (  # noqa: F401
    add_favorite,
    ensure_user,
    get_preferences,
    get_rating,
    list_favorites,
    list_ratings,
    remove_favorite,
    set_preferences,
    upsert_rating,
)
