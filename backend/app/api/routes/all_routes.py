"""All API routes grouped by tag in a single module for compactness.

Routes are registered under /api/v1 by main.py."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ModelNotTrainedError, NotFoundError
from app.db.base import get_db
from app.integrations.tmdb import tmdb
from app.recommender.registry import registry
from app.schemas.schemas import (
    AnalyticsOverview,
    DatasetSummary,
    FavoriteCreate,
    FavoriteOut,
    Genre,
    ModelComparison,
    ModelMetrics,
    MoviePage,
    MovieWithStats,
    PreferenceOut,
    PreferenceUpdate,
    RatingCreate,
    RatingOut,
    RecommendationList,
    RecommendationRequest,
)
from app.services import domain


# ---------------- system ----------------

system_router = APIRouter(tags=["system"])


@system_router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": settings.app_version}


@system_router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    registry.load()
    catalogue_ready = not registry.movies.empty and not registry.ratings.empty
    return {
        "status": "ok" if catalogue_ready else "degraded",
        "readiness": {
            "api_process": True,
            "database": True,
            "catalogue_loaded": catalogue_ready,
            "popularity_ready": registry.popularity.is_ready(),
            "content_ready": registry.content.is_ready(),
            "collaborative_ready": registry.cf.is_ready(),
            "hybrid_ready": registry.hybrid.is_ready(),
            "tmdb_enabled": tmdb.enabled,
        },
    }


# ---------------- movies ----------------

movies_router = APIRouter(prefix="/movies", tags=["movies"])


@movies_router.get("", response_model=MoviePage)
def list_movies_ep(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, max_length=120),
    genre: str | None = Query(default=None, max_length=40),
    year_min: int | None = Query(default=None, ge=1900, le=2100),
    year_max: int | None = Query(default=None, ge=1900, le=2100),
    page: int = Query(default=1, ge=1, le=1000),
    page_size: int = Query(default=25, ge=1, le=100),
    sort: str = Query(default="popularity", pattern="^(popularity|rating|title|year)$"),
):
    registry.load()
    return domain.list_movies(
        db, page=page, page_size=page_size, q=q, genre=genre,
        year_min=year_min, year_max=year_max, sort=sort,
    )


@movies_router.get("/search", response_model=MoviePage)
def search_movies_ep(
    q: str = Query(..., min_length=1, max_length=120),
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    registry.load()
    return domain.list_movies(db, q=q, page=page, page_size=page_size)


@movies_router.get("/{movie_id}", response_model=MovieWithStats)
def get_movie_ep(movie_id: int, db: Session = Depends(get_db)):
    registry.load()
    row = domain.get_movie(db, movie_id)
    if tmdb.enabled and row.tmdb_id:
        poster = tmdb.poster_url(int(row.tmdb_id))
        if poster:
            row.poster_url = poster
    return row


@movies_router.get("", name="genres_alias")
def _duplicate_guard():  # pragma: no cover
    raise NotImplementedError


genres_router = APIRouter(prefix="/genres", tags=["movies"])


@genres_router.get("", response_model=list[Genre])
def genres_ep(db: Session = Depends(get_db)):
    registry.load()
    return domain.list_genres(db)


# ---------------- recommendations ----------------

recs_router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@recs_router.get("/popular", response_model=RecommendationList)
def popular_ep(
    db: Session = Depends(get_db),
    user_id: int | None = Query(default=None, ge=1),
    top_k: int = Query(default=20, ge=1, le=100),
):
    registry.load()
    return domain.recommendations_popular(db, user_id=user_id, top_k=top_k)


@recs_router.get("/similar/{movie_id}", response_model=RecommendationList)
def similar_ep(movie_id: int, db: Session = Depends(get_db), top_k: int = Query(20, ge=1, le=50)):
    registry.load()
    return domain.recommendations_similar(db, movie_id, top_k=top_k)


@recs_router.get("/users/{user_id}", response_model=RecommendationList)
def for_user_get_ep(
    user_id: int,
    db: Session = Depends(get_db),
    strategy: str = Query("hybrid", pattern="^(hybrid|popularity|content|collaborative)$"),
    top_k: int = Query(20, ge=1, le=100),
):
    registry.load()
    return domain.recommendations_for_user(db, user_id=user_id, strategy=strategy, top_k=top_k)


@recs_router.post("", response_model=RecommendationList)
def for_user_post_ep(body: RecommendationRequest, db: Session = Depends(get_db)):
    registry.load()
    return domain.recommendations_for_user(
        db,
        user_id=body.user_id,
        strategy=body.strategy,
        top_k=body.top_k,
        genres=body.genres,
        year_min=body.year_min,
        year_max=body.year_max,
        exclude_rated=body.exclude_rated,
    )


@recs_router.get("/explanations/{movie_id}")
def explain_ep(
    movie_id: int,
    db: Session = Depends(get_db),
    user_id: int | None = Query(default=None, ge=1),
):
    registry.load()
    row = registry.catalogue_row(movie_id)
    if row is None:
        raise NotFoundError(f"Movie {movie_id} not found.")
    from app.recommender import explanations as explain_mod
    from app.recommender.base import Scored
    seed_ids: list[int] = []
    if user_id is not None:
        pref = db and __import__(
            "app.repositories.repository", fromlist=["get_preferences"]
        ).get_preferences(db, user_id)
        if pref is not None:
            seed_ids = [int(x) for x in (pref.seed_movie_ids or [])]
        if not seed_ids:
            ratings = db and __import__(
                "app.repositories.repository", fromlist=["list_ratings"]
            ).list_ratings(db, user_id)
            if ratings:
                top = sorted(ratings, key=lambda r: -int(r.value))[:10]
                seed_ids = [int(r.movie_id) for r in top]
    sc = Scored(movie_id=int(movie_id), score=0.0, components={})
    if registry.popularity.is_ready():
        st = registry.popularity.stats(movie_id)
        if st:
            sc.components["popularity"] = st["score"]
    if seed_ids and registry.content.is_ready():
        sim = registry.content.profile_similarity(movie_id, seed_ids)
        if sim is not None:
            sc.components["content"] = sim
    reasons = explain_mod.explain(sc, row, seed_ids or None, registry.content, registry.cf, user_id)
    return {
        "movie_id": movie_id,
        "user_id": user_id,
        "personalized": bool(seed_ids),
        "reasons": [
            {"kind": "hybrid", "text": t} for t in reasons
        ],
    }


# ---------------- users (ratings / favorites / preferences) ----------------

users_router = APIRouter(tags=["users"])


@users_router.post("/ratings", response_model=RatingOut, status_code=status.HTTP_201_CREATED)
def rate_ep(body: RatingCreate, db: Session = Depends(get_db)):
    return domain.put_rating(db, body.user_id, body.movie_id, body.value)


@users_router.get("/users/{user_id}/ratings", response_model=list[RatingOut])
def list_ratings_ep(user_id: int, db: Session = Depends(get_db)):
    return domain.get_ratings(db, user_id)


@users_router.post("/users/{user_id}/favorites", response_model=FavoriteOut, status_code=status.HTTP_201_CREATED)
def add_fav_ep(user_id: int, body: FavoriteCreate, db: Session = Depends(get_db)):
    return domain.add_favorite(db, user_id, body.movie_id)


@users_router.delete("/users/{user_id}/favorites/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def del_fav_ep(user_id: int, movie_id: int, db: Session = Depends(get_db)):
    domain.remove_favorite(db, user_id, movie_id)
    return None


@users_router.get("/users/{user_id}/favorites", response_model=list[FavoriteOut])
def list_fav_ep(user_id: int, db: Session = Depends(get_db)):
    return domain.get_favorites(db, user_id)


@users_router.put("/users/{user_id}/preferences", response_model=PreferenceOut)
def put_pref_ep(user_id: int, body: PreferenceUpdate, db: Session = Depends(get_db)):
    return domain.put_preferences(db, user_id, body.genres, body.seed_movie_ids)


@users_router.get("/users/{user_id}/preferences", response_model=PreferenceOut)
def get_pref_ep(user_id: int, db: Session = Depends(get_db)):
    return domain.get_preferences(db, user_id)


# ---------------- analytics ----------------

analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


def _model_version() -> str | None:
    v = settings.artifacts_dir / "model_version.json"
    if not v.exists():
        return None
    try:
        return json.loads(v.read_text(encoding="utf-8")).get("version")
    except Exception:
        return None


@analytics_router.get("/overview", response_model=AnalyticsOverview)
def overview_ep(db: Session = Depends(get_db)):
    registry.load()
    summary: DatasetSummary | None = None
    if registry.summary:
        s = registry.summary
        summary = DatasetSummary(
            dataset_version=s.get("dataset_version", settings.movielens_dataset),
            n_users=int(s.get("n_users", 0)),
            n_movies=int(s.get("n_movies", 0)),
            n_ratings=int(s.get("n_ratings", 0)),
            n_genres=int(s.get("n_genres", 0)),
            missing_values=dict(s.get("missing_values", {})),
        )
    return AnalyticsOverview(
        dataset=summary,
        model_version=_model_version(),
        n_fitted_users=registry.cf.fitted_user_count() if registry.cf.is_ready() else 0,
        n_catalog_movies=int(len(registry.movies)) if not registry.movies.empty else 0,
    )


@analytics_router.get("/model-comparison", response_model=ModelComparison)
def compare_ep(db: Session = Depends(get_db)):
    p = Path(settings.artifacts_dir) / "evaluation.json"
    if not p.exists():
        raise ModelNotTrainedError(
            "Evaluation results not available. Run scripts/evaluate_models.py first."
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    metrics = [ModelMetrics(**row) for row in data.get("metrics", [])]
    return ModelComparison(
        protocol=data.get("protocol", "unknown"),
        top_k=int(data.get("top_k", 10)),
        metrics=metrics,
    )
