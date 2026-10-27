"""Services re-export."""
from app.services.domain import (  # noqa: F401
    add_favorite,
    get_favorites,
    get_movie,
    get_preferences,
    get_ratings,
    list_genres,
    list_movies,
    put_preferences,
    put_rating,
    recommendations_for_user,
    recommendations_popular,
    recommendations_similar,
    remove_favorite,
)
