"""Domain services. Joins the recommender registry with the DB layer and
maps Scored lists into API-shaped RecommendationList objects.

Also handles user preference enrichment: user's DB ratings are merged with
dataset-side ratings so the recommender always sees the fullest profile."""
from __future__ import annotations

from typing import Iterable

import pandas as pd
from sqlalchemy.orm import Session

from app.core.exceptions import ModelNotTrainedError, NotFoundError
from app.recommender import explanations as explain_mod
from app.recommender.base import Scored
from app.recommender.registry import registry
from app.repositories import repository as repo
from app.schemas.schemas import (
    FavoriteOut,
    Genre,
    Movie,
    MoviePage,
    MovieWithStats,
    PreferenceOut,
    RatingOut,
    RecommendedMovie,
    RecommendationList,
    RecommendationReason,
)


# ---------- Catalogue helpers ----------

def _row_to_movie(row: pd.Series) -> Movie:
    return Movie(
        movie_id=int(row["movie_id"]),
        title=str(row["title"]),
        release_year=(
            int(row["release_year"]) if pd.notna(row.get("release_year")) else None
        ),
        genres=str(row.get("genres", "") or "").split("|") if row.get("genres") else [],
    )


def _attach_stats(movies: Iterable[pd.Series]) -> list[MovieWithStats]:
    out: list[MovieWithStats] = []
    for row in movies:
        stats = registry.popularity.stats(int(row["movie_id"])) or {
            "mean_rating": 0.0, "rating_count": 0,
        }
        m = _row_to_movie(row)
        out.append(MovieWithStats(
            **m.model_dump(),
            rating_count=int(stats.get("rating_count", 0)),
            mean_rating=round(float(stats.get("mean_rating", 0.0)), 3),
        ))
    return out


# ---------- Movie listing / search ----------

def list_movies(
    session: Session,
    page: int = 1,
    page_size: int = 25,
    q: str | None = None,
    genre: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    sort: str = "popularity",
) -> MoviePage:
    registry.load()
    if registry.movies.empty:
        raise ModelNotTrainedError("Catalogue not loaded. Run preprocessing first.")
    df = registry.movies.copy()
    if q:
        df = df[df["title"].str.contains(q, case=False, na=False)]
    if genre:
        df = df[df["genres"].str.contains(f"(^|\\|){genre}($|\\|)", regex=True, na=False)]
    if year_min is not None:
        df = df[df["release_year"] >= year_min]
    if year_max is not None:
        df = df[df["release_year"] <= year_max]

    if sort == "title":
        df = df.sort_values("title", kind="stable")
    elif sort == "year":
        df = df.sort_values("release_year", ascending=False, na_position="last", kind="stable")
    elif sort == "rating":
        stats = registry.popularity._table
        means = pd.Series({mid: stats.mean_ratings[i] for mid, i in stats.index.items()})
        df["__mean"] = df["movie_id"].map(means)
        df = df.sort_values("__mean", ascending=False, na_position="last", kind="stable")
        df = df.drop(columns=["__mean"])
    else:  # popularity
        stats = registry.popularity._table
        scores = pd.Series({mid: stats.scores[i] for mid, i in stats.index.items()})
        df["__score"] = df["movie_id"].map(scores)
        df = df.sort_values("__score", ascending=False, na_position="last", kind="stable")
        df = df.drop(columns=["__score"])

    total = int(len(df))
    start = max(0, (page - 1) * page_size)
    page_rows = df.iloc[start : start + page_size]
    return MoviePage(
        items=_attach_stats(row for _, row in page_rows.iterrows()),
        total=total,
        page=page,
        page_size=page_size,
    )


def get_movie(session: Session, movie_id: int) -> MovieWithStats:
    registry.load()
    row = registry.catalogue_row(movie_id)
    if row is None:
        raise NotFoundError(f"Movie {movie_id} not found.")
    return _attach_stats([row])[0]


def list_genres(session: Session) -> list[Genre]:
    registry.load()
    counts: dict[str, int] = {}
    for g in registry.movies["genres"].fillna(""):
        for name in str(g).split("|"):
            name = name.strip()
            if name:
                counts[name] = counts.get(name, 0) + 1
    return [Genre(name=k, movie_count=v) for k, v in sorted(counts.items())]


# ---------- Recommendations ----------

def _scored_to_recommended(
    scored: Scored,
    catalogue_row: pd.Series,
    user_seed_ids: list[int] | None,
) -> RecommendedMovie:
    stats = registry.popularity.stats(scored.movie_id) or {}
    m = _row_to_movie(catalogue_row)
    movie_stats = MovieWithStats(
        **m.model_dump(),
        rating_count=int(stats.get("rating_count", 0)),
        mean_rating=round(float(stats.get("mean_rating", 0.0)), 3),
    )
    reasons = explain_mod.explain(
        scored=scored,
        catalogue_row=catalogue_row,
        user_seed_movie_ids=user_seed_ids,
        content=registry.content,
        cf=registry.cf,
    )
    return RecommendedMovie(
        movie=movie_stats,
        score=round(scored.score, 5),
        reasons=[RecommendationReason(kind="hybrid", text=r) for r in reasons],
        component_scores={k: round(v, 5) for k, v in scored.components.items()},
    )


def recommendations_similar(
    session: Session, movie_id: int, top_k: int = 20
) -> RecommendationList:
    registry.load()
    src = registry.catalogue_row(movie_id)
    if src is None:
        raise NotFoundError(f"Movie {movie_id} not found.")
    scored_list = registry.content.similar_to_movie(movie_id, exclude_movie_ids=None, top_k=top_k)
    items: list[RecommendedMovie] = []
    for sc in scored_list:
        row = registry.catalogue_row(sc.movie_id)
        if row is None:
            continue
        sc.components.setdefault("content", sc.score)
        items.append(_scored_to_recommended(sc, row, user_seed_ids=[int(movie_id)]))
    return RecommendationList(
        strategy="content",
        based_on_movie_id=int(movie_id),
        items=items,
        personalized=False,
        notes=["Similarity is computed on TF-IDF over genres + title tokens."],
    )


def recommendations_popular(
    session: Session, user_id: int | None = None, top_k: int = 20
) -> RecommendationList:
    registry.load()
    exclude: set[int] = set()
    if user_id is not None:
        exclude = {int(r.movie_id) for r in repo.list_ratings(session, user_id)}
    scored_list = registry.popularity.global_top(top_k=top_k, exclude_movie_ids=exclude)
    items: list[RecommendedMovie] = []
    for sc in scored_list:
        row = registry.catalogue_row(sc.movie_id)
        if row is None:
            continue
        sc.components = {"popularity": sc.score}
        items.append(_scored_to_recommended(sc, row, user_seed_ids=None))
    return RecommendationList(
        strategy="popularity",
        user_id=user_id,
        items=items,
        personalized=False,
        notes=["Bayesian weighted rating with min-support threshold."],
    )


def recommendations_for_user(
    session: Session, user_id: int, strategy: str, top_k: int,
    genres: list[str] | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    exclude_rated: bool = True,
) -> RecommendationList:
    registry.load()
    # Merge dataset + user-generated ratings for a richer profile.
    ds_ratings = registry.user_ratings(user_id)
    user_rows = repo.list_ratings(session, user_id) if user_id is not None else []
    merged = pd.Series(dtype=float)
    if ds_ratings is not None:
        merged = merged.append(ds_ratings)
    for r in user_rows:
        merged[int(r.movie_id)] = float(r.value)
    exclude = set(int(x) for x in merged.index.tolist()) if exclude_rated else set()

    # Pref from DB (seed genres / movies).
    pref = repo.get_preferences(session, user_id) if user_id is not None else None
    seed_ids: list[int] = []
    if pref is not None:
        seed_ids.extend([int(x) for x in (pref.seed_movie_ids or [])])
    if not seed_ids and not merged.empty:
        top = merged.sort_values(ascending=False).head(10)
        seed_ids = [int(x) for x in top.index]

    # Optional user preference genres -> also allow the caller to override via
    # the request `genres` filter.
    filter_genres = set(genres or [])
    if pref is not None and not filter_genres:
        filter_genres = {g for g in (pref.genres or []) if g}

    # Dispatch to the right strategy.
    if strategy == "popularity":
        scored_list = registry.popularity.global_top(top_k=top_k * 3, exclude_movie_ids=exclude)
    elif strategy == "content":
        if not seed_ids:
            scored_list = registry.popularity.global_top(top_k=top_k, exclude_movie_ids=exclude)
        else:
            # Aggregate similar-to-seed.
            agg: dict[int, float] = {}
            for sid in seed_ids:
                for sc in registry.content.similar_to_movie(sid, exclude_movie_ids=exclude, top_k=top_k * 2):
                    agg[sc.movie_id] = agg.get(sc.movie_id, 0.0) + sc.score
            pairs = sorted(agg.items(), key=lambda x: (-x[1], x[0]))[:top_k]
            from app.recommender.base import Scored as _S
            scored_list = [_S(movie_id=mid, score=s, components={"content": s}) for mid, s in pairs]
    elif strategy == "collaborative":
        scored_list = registry.cf.top_for_user(user_id, merged if not merged.empty else None, exclude, top_k)
        if not scored_list:  # Cold-start -> fallback to popularity.
            scored_list = registry.popularity.global_top(top_k=top_k, exclude_movie_ids=exclude)
    else:  # hybrid
        scored_list = registry.hybrid.rank(
            user_id=user_id,
            ratings_by_user=merged if not merged.empty else None,
            exclude_movie_ids=exclude,
            top_k=top_k * 3,
            seed_movie_ids=seed_ids or None,
        )

    # Post-filter (genre/year).
    items: list[RecommendedMovie] = []
    for sc in scored_list:
        row = registry.catalogue_row(sc.movie_id)
        if row is None:
            continue
        if filter_genres:
            genres_of_row = set(str(row.get("genres", "") or "").split("|"))
            if not (genres_of_row & filter_genres):
                continue
        year = row.get("release_year")
        if pd.notna(year):
            y = int(year)
            if year_min is not None and y < year_min:
                continue
            if year_max is not None and y > year_max:
                continue
        items.append(_scored_to_recommended(sc, row, user_seed_ids=seed_ids or None))
        if len(items) >= top_k:
            break

    is_personalized = (
        strategy != "popularity"
        and explain_mod.personalized_flag(user_id, registry.cf)
    )
    notes: list[str] = []
    if strategy == "collaborative" and not registry.cf.user_has_history(user_id):
        notes.append("No collaborative history found for this user; fell back to popularity.")
    if not is_personalized and strategy == "hybrid" and not seed_ids:
        notes.append("Hybrid running without personalised seeds (cold-start).")

    return RecommendationList(
        strategy=strategy,
        user_id=user_id,
        items=items,
        personalized=is_personalized,
        notes=notes,
    )


# ---------- Users: ratings / favorites / preferences ----------

def put_rating(session: Session, user_id: int, movie_id: int, value: int) -> RatingOut:
    registry.load()
    if registry.catalogue_row(movie_id) is None:
        raise NotFoundError(f"Movie {movie_id} not found.")
    row = repo.upsert_rating(session, user_id, movie_id, int(value))
    return RatingOut(
        user_id=row.user_id, movie_id=row.movie_id,
        value=int(row.value), updated_at=row.updated_at,
    )


def get_ratings(session: Session, user_id: int) -> list[RatingOut]:
    return [
        RatingOut(user_id=r.user_id, movie_id=r.movie_id, value=int(r.value), updated_at=r.updated_at)
        for r in repo.list_ratings(session, user_id)
    ]


def add_favorite(session: Session, user_id: int, movie_id: int) -> FavoriteOut:
    registry.load()
    if registry.catalogue_row(movie_id) is None:
        raise NotFoundError(f"Movie {movie_id} not found.")
    row = repo.add_favorite(session, user_id, movie_id)
    return FavoriteOut(user_id=row.user_id, movie_id=row.movie_id, created_at=row.created_at)


def remove_favorite(session: Session, user_id: int, movie_id: int) -> None:
    repo.remove_favorite(session, user_id, movie_id)


def get_favorites(session: Session, user_id: int) -> list[FavoriteOut]:
    return [
        FavoriteOut(user_id=r.user_id, movie_id=r.movie_id, created_at=r.created_at)
        for r in repo.list_favorites(session, user_id)
    ]


def put_preferences(session: Session, user_id: int, genres: list[str], seed_movie_ids: list[int]) -> PreferenceOut:
    registry.load()
    for mid in seed_movie_ids:
        if registry.catalogue_row(mid) is None:
            raise NotFoundError(f"Movie {mid} not found.")
    row = repo.set_preferences(session, user_id, genres, seed_movie_ids)
    return PreferenceOut(
        user_id=row.user_id, genres=list(row.genres or []),
        seed_movie_ids=[int(x) for x in (row.seed_movie_ids or [])],
        updated_at=row.updated_at,
    )


def get_preferences(session: Session, user_id: int) -> PreferenceOut:
    row = repo.get_preferences(session, user_id)
    if row is None:
        return PreferenceOut(user_id=user_id, genres=[], seed_movie_ids=[], updated_at=pd.Timestamp.now().to_pydatetime())
    return PreferenceOut(
        user_id=row.user_id, genres=list(row.genres or []),
        seed_movie_ids=[int(x) for x in (row.seed_movie_ids or [])],
        updated_at=row.updated_at,
    )
