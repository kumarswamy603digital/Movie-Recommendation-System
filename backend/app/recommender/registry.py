"""Recommender + catalogue singleton loaded once at app startup.

Loads three artifacts produced by `scripts/train_models.py`:
- popularity.joblib
- content.joblib
- collaborative.joblib
Plus the preprocessed CSVs produced by `scripts/preprocess_data.py`:
- movies.csv  (movie_id, title, release_year, genres - pipe-joined)
- ratings.csv (user_id, movie_id, rating, timestamp)
- summary.json

Missing artifacts leave the recommender in an *unready* state - the /ready
endpoint reports this honestly. Handlers raise ModelNotTrainedError rather
than fabricating a response.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.core.logging import get_logger
from app.recommender.collaborative import CollaborativeRecommender
from app.recommender.content_based import ContentBasedRecommender
from app.recommender.hybrid import HybridRecommender, HybridWeights
from app.recommender.popularity import PopularityRecommender

log = get_logger("app.recommender.registry")


class Registry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loaded = False
        self.movies: pd.DataFrame = pd.DataFrame()
        self.ratings: pd.DataFrame = pd.DataFrame()
        self.popularity = PopularityRecommender()
        self.content = ContentBasedRecommender()
        self.cf = CollaborativeRecommender()
        self.hybrid = HybridRecommender(
            self.popularity, self.content, self.cf,
            weights=HybridWeights(
                settings.hybrid_weight_popularity,
                settings.hybrid_weight_content,
                settings.hybrid_weight_collaborative,
            ),
        )
        self.summary: dict = {}

    # ---------- state ----------

    @property
    def loaded(self) -> bool:
        return self._loaded

    def catalogue_row(self, movie_id: int) -> pd.Series | None:
        if self.movies.empty:
            return None
        row = self.movies.loc[self.movies["movie_id"] == int(movie_id)]
        return None if row.empty else row.iloc[0]

    def movie_ids_for(self, movie_ids: list[int] | set[int]) -> pd.DataFrame:
        if self.movies.empty:
            return pd.DataFrame()
        return self.movies[self.movies["movie_id"].isin([int(m) for m in movie_ids])]

    def user_ratings(self, user_id: int) -> pd.Series | None:
        if self.ratings.empty:
            return None
        sub = self.ratings[self.ratings["user_id"] == int(user_id)]
        if sub.empty:
            return None
        return sub.set_index("movie_id")["rating"]

    # ---------- loading ----------

    def load(self, force: bool = False) -> None:
        with self._lock:
            if self._loaded and not force:
                return
            self._load_locked()

    def _load_locked(self) -> None:
        data_dir = settings.processed_dir
        art_dir = settings.artifacts_dir
        movies_p = Path(data_dir) / "movies.csv"
        ratings_p = Path(data_dir) / "ratings.csv"
        summary_p = Path(data_dir) / "summary.json"
        pop_p = Path(art_dir) / "popularity.joblib"
        con_p = Path(art_dir) / "content.joblib"
        cf_p = Path(art_dir) / "collaborative.joblib"

        if not movies_p.exists() or not ratings_p.exists():
            log.warning(
                "Preprocessed CSVs missing at %s. Run scripts/preprocess_data.py first.",
                data_dir,
            )
            self._loaded = False
            return

        self.movies = pd.read_csv(movies_p)
        self.ratings = pd.read_csv(ratings_p)
        if summary_p.exists():
            self.summary = json.loads(summary_p.read_text(encoding="utf-8"))

        # Recommenders: load if artifacts exist, else fit lazily from CSVs so
        # the service is usable without a separate training step for small
        # datasets.
        if pop_p.exists():
            self.popularity = PopularityRecommender.load(str(pop_p))
        else:
            log.info("Fitting popularity on demand ...")
            self.popularity = PopularityRecommender.fit(
                self.ratings, min_ratings=settings.popularity_min_ratings
            )

        if con_p.exists():
            self.content = ContentBasedRecommender.load(str(con_p))
        else:
            log.info("Fitting content index on demand ...")
            self.content = ContentBasedRecommender.fit(self.movies)

        if cf_p.exists():
            self.cf = CollaborativeRecommender.load(str(cf_p))
        else:
            log.info("Fitting collaborative on demand ...")
            self.cf = CollaborativeRecommender.fit(self.ratings)

        self.hybrid = HybridRecommender(
            self.popularity, self.content, self.cf,
            weights=HybridWeights(
                settings.hybrid_weight_popularity,
                settings.hybrid_weight_content,
                settings.hybrid_weight_collaborative,
            ),
        )
        self._loaded = True
        log.info(
            "Recommender registry loaded: %d movies, %d ratings.",
            len(self.movies), len(self.ratings),
        )


registry = Registry()
