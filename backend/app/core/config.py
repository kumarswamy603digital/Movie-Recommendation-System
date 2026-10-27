"""Backend configuration loaded from environment (12-factor style)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core
    app_name: str = "Movie Recommendation System"
    app_version: str = "1.0.0"
    environment: str = Field(default="development")

    # CORS
    cors_origins: str = Field(default="http://localhost:5173")

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Database
    database_url: str = "sqlite:///./app.db"

    # Dataset
    movielens_dataset: str = Field(default="ml-100k")
    data_dir: Path = Path("./data")
    artifacts_dir: Path = Path("./artifacts")

    # Recommender tuning
    popularity_min_ratings: int = 20
    hybrid_weight_popularity: float = 0.20
    hybrid_weight_content: float = 0.35
    hybrid_weight_collaborative: float = 0.45

    # TMDB (optional)
    tmdb_api_key: str = ""
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p/w500"
    tmdb_timeout_seconds: float = 5.0

    # Demo user (LOCAL DEMO MODE - not real auth)
    demo_user_id: int = 1
    demo_user_email: str = "demo@example.com"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def dataset_dir(self) -> Path:
        return self.data_dir / self.movielens_dataset

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def tmdb_enabled(self) -> bool:
        return bool(self.tmdb_api_key.strip())

    @field_validator("movielens_dataset")
    @classmethod
    def _validate_dataset(cls, v: str) -> str:
        allowed = {"ml-100k", "ml-1m", "ml-25m"}
        if v not in allowed:
            raise ValueError(f"movielens_dataset must be one of {sorted(allowed)}")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
