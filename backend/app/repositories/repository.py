"""Data access layer for user-owned data (SQLAlchemy sessions).

Kept intentionally thin: encapsulates persistence primitives so that services
and routes never write raw queries."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.db_models import Favorite, Preference, Rating, User


# ---------- Users ----------

def ensure_user(session: Session, user_id: int, email: str | None = None) -> User:
    """Return a User row, creating a demo-mode row if it does not exist.

    The application runs in *local demo mode*: we trust client-provided
    ``user_id`` values. Production deployments must add real authentication.
    """
    user = session.get(User, user_id)
    if user is not None:
        return user
    user = User(id=user_id, email=email or f"user_{user_id}@example.com", is_demo=True)
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        user = session.get(User, user_id)
        if user is None:
            raise ConflictError("Could not create user.")
    return user


# ---------- Ratings ----------

def upsert_rating(session: Session, user_id: int, movie_id: int, value: int) -> Rating:
    ensure_user(session, user_id)
    existing = session.scalar(
        select(Rating).where(Rating.user_id == user_id, Rating.movie_id == movie_id)
    )
    if existing is not None:
        existing.value = value
        session.flush()
        return existing
    row = Rating(user_id=user_id, movie_id=movie_id, value=value)
    session.add(row)
    session.flush()
    return row


def list_ratings(session: Session, user_id: int) -> list[Rating]:
    return list(session.scalars(select(Rating).where(Rating.user_id == user_id)))


def get_rating(session: Session, user_id: int, movie_id: int) -> Rating | None:
    return session.scalar(
        select(Rating).where(Rating.user_id == user_id, Rating.movie_id == movie_id)
    )


# ---------- Favorites ----------

def add_favorite(session: Session, user_id: int, movie_id: int) -> Favorite:
    ensure_user(session, user_id)
    existing = session.scalar(
        select(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
    )
    if existing is not None:
        return existing
    row = Favorite(user_id=user_id, movie_id=movie_id)
    session.add(row)
    session.flush()
    return row


def remove_favorite(session: Session, user_id: int, movie_id: int) -> None:
    result = session.execute(
        delete(Favorite).where(Favorite.user_id == user_id, Favorite.movie_id == movie_id)
    )
    if result.rowcount == 0:
        raise NotFoundError("Favorite not found for this user/movie.")


def list_favorites(session: Session, user_id: int) -> list[Favorite]:
    return list(session.scalars(select(Favorite).where(Favorite.user_id == user_id)))


# ---------- Preferences ----------

def set_preferences(
    session: Session, user_id: int, genres: list[str], seed_movie_ids: list[int]
) -> Preference:
    ensure_user(session, user_id)
    pref = session.scalar(select(Preference).where(Preference.user_id == user_id))
    if pref is None:
        pref = Preference(user_id=user_id, genres=genres, seed_movie_ids=seed_movie_ids)
        session.add(pref)
    else:
        pref.genres = genres
        pref.seed_movie_ids = seed_movie_ids
    session.flush()
    return pref


def get_preferences(session: Session, user_id: int) -> Preference | None:
    return session.scalar(select(Preference).where(Preference.user_id == user_id))
