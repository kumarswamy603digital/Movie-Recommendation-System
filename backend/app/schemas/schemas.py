"""Pydantic v2 schemas. One module for the whole API surface."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --------- Movie catalogue ---------

class Movie(BaseModel):
    movie_id: int
    title: str
    release_year: int | None = None
    genres: list[str] = Field(default_factory=list)
    tmdb_id: int | None = None
    poster_url: str | None = None
    overview: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MovieWithStats(Movie):
    rating_count: int
    mean_rating: float


class MoviePage(BaseModel):
    items: list[MovieWithStats]
    total: int
    page: int
    page_size: int


class Genre(BaseModel):
    name: str
    movie_count: int


# --------- Recommendations ---------

class RecommendationReason(BaseModel):
    """Structured, honest explanation for a single recommendation."""
    kind: Literal["content", "collaborative", "popularity", "hybrid", "onboarding"]
    text: str


class RecommendedMovie(BaseModel):
    movie: MovieWithStats
    score: float
    reasons: list[RecommendationReason] = Field(default_factory=list)
    component_scores: dict[str, float] = Field(default_factory=dict)


class RecommendationList(BaseModel):
    strategy: str
    user_id: int | None = None
    based_on_movie_id: int | None = None
    items: list[RecommendedMovie]
    personalized: bool
    notes: list[str] = Field(default_factory=list)


class RecommendationRequest(BaseModel):
    user_id: int
    strategy: Literal["hybrid", "popularity", "content", "collaborative"] = "hybrid"
    top_k: int = Field(default=20, ge=1, le=100)
    genres: list[str] | None = None
    year_min: int | None = Field(default=None, ge=1900, le=2100)
    year_max: int | None = Field(default=None, ge=1900, le=2100)
    exclude_rated: bool = True


# --------- User interactions ---------

class RatingCreate(BaseModel):
    user_id: int
    movie_id: int
    value: int = Field(ge=1, le=5)


class RatingOut(BaseModel):
    user_id: int
    movie_id: int
    value: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FavoriteCreate(BaseModel):
    movie_id: int


class FavoriteOut(BaseModel):
    user_id: int
    movie_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreferenceUpdate(BaseModel):
    genres: list[str] = Field(default_factory=list)
    seed_movie_ids: list[int] = Field(default_factory=list)

    @field_validator("genres")
    @classmethod
    def _clean_genres(cls, v: list[str]) -> list[str]:
        return sorted({g.strip() for g in v if g.strip()})


class PreferenceOut(BaseModel):
    user_id: int
    genres: list[str]
    seed_movie_ids: list[int]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --------- Analytics / system ---------

class DatasetSummary(BaseModel):
    dataset_version: str
    n_users: int
    n_movies: int
    n_ratings: int
    n_genres: int
    missing_values: dict[str, int]
    processed_at: datetime | None = None


class ModelMetrics(BaseModel):
    model: str
    evaluation_date: str | None = None
    top_k: int | None = None
    precision_at_k: float | None = None
    recall_at_k: float | None = None
    ndcg_at_k: float | None = None
    coverage: float | None = None
    rmse: float | None = None
    mae: float | None = None
    notes: str | None = None


class AnalyticsOverview(BaseModel):
    dataset: DatasetSummary | None
    model_version: str | None
    n_fitted_users: int | None
    n_catalog_movies: int | None


class ModelComparison(BaseModel):
    protocol: str
    top_k: int
    metrics: list[ModelMetrics]
