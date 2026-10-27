"""Fit popularity, content-based, and collaborative recommenders, save artifacts.

Usage:
    python -m scripts.train_models
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings  # noqa: E402
from app.recommender.collaborative import CollaborativeRecommender  # noqa: E402
from app.recommender.content_based import ContentBasedRecommender  # noqa: E402
from app.recommender.popularity import PopularityRecommender  # noqa: E402


def main() -> int:
    processed = Path(settings.processed_dir)
    if not (processed / "movies.csv").exists() or not (processed / "ratings.csv").exists():
        print("Processed CSVs missing. Run scripts.preprocess_data first.", file=sys.stderr)
        return 2

    movies = pd.read_csv(processed / "movies.csv")
    ratings = pd.read_csv(processed / "ratings.csv")
    print(f"Loaded {len(movies):,} movies, {len(ratings):,} ratings.")

    arts = Path(settings.artifacts_dir)
    arts.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    pop = PopularityRecommender.fit(ratings, min_ratings=settings.popularity_min_ratings)
    pop.save(str(arts / "popularity.joblib"))
    print(f"  [ok] popularity       (rows={len(pop._table.movie_ids):,})")

    t1 = time.perf_counter()
    con = ContentBasedRecommender.fit(movies)
    con.save(str(arts / "content.joblib"))
    print(f"  [ok] content_based    (vocab={len(con._idx.vectorizer.vocabulary_):,})")

    t2 = time.perf_counter()
    cf = CollaborativeRecommender.fit(ratings)
    cf.save(str(arts / "collaborative.joblib"))
    print(f"  [ok] collaborative    (users={cf._st.user_ids.size:,} items={cf._st.movie_ids.size:,})")

    version = {
        "version": time.strftime("%Y.%m.%d-%H%M%S"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": settings.movielens_dataset,
        "n_movies": int(len(movies)),
        "n_ratings": int(len(ratings)),
        "weights": {
            "popularity": settings.hybrid_weight_popularity,
            "content": settings.hybrid_weight_content,
            "collaborative": settings.hybrid_weight_collaborative,
        },
        "fit_seconds": {
            "popularity": round(time.perf_counter() - t0, 3),
            "content": round(t2 - t1, 3),
            "collaborative": round(time.perf_counter() - t2, 3),
        },
        "popularity_min_ratings": settings.popularity_min_ratings,
    }
    (arts / "model_version.json").write_text(json.dumps(version, indent=2), encoding="utf-8")
    print(f"Artifacts saved to {arts}")
    print(json.dumps(version, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
