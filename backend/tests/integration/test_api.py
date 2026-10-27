"""Integration tests for the FastAPI app.

These use a synthetic in-memory catalogue to avoid depending on the real
MovieLens pipeline having been run. The registry is monkeypatched with tiny
fitted recommenders so we exercise the full request path."""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.recommender.collaborative import CollaborativeRecommender
from app.recommender.content_based import ContentBasedRecommender
from app.recommender.hybrid import HybridRecommender
from app.recommender.popularity import PopularityRecommender
from app.recommender.registry import registry


@pytest.fixture
def client(db_session, tiny_ratings, tiny_movies):
    # Fit recommenders on tiny fixtures.
    registry.movies = tiny_movies
    registry.ratings = tiny_ratings
    registry.popularity = PopularityRecommender.fit(tiny_ratings, min_ratings=1)
    registry.content = ContentBasedRecommender.fit(tiny_movies)
    registry.cf = CollaborativeRecommender.fit(tiny_ratings, svd_components=0)
    registry.hybrid = HybridRecommender(registry.popularity, registry.content, registry.cf)
    registry._loaded = True

    from app.main import app
    from app.db.base import get_db

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_ready_flags(client):
    r = client.get("/api/v1/ready")
    body = r.json()
    assert body["readiness"]["catalogue_loaded"] is True
    assert body["readiness"]["collaborative_ready"] is True


def test_movies_listing_pagination(client):
    r = client.get("/api/v1/movies?page=1&page_size=2")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) <= 2
    assert body["total"] >= 2


def test_movies_filter_by_genre(client):
    r = client.get("/api/v1/movies?genre=Sci-Fi")
    body = r.json()
    for item in body["items"]:
        assert "Sci-Fi" in item["genres"]


def test_get_movie_and_missing(client):
    r = client.get("/api/v1/movies/10")
    assert r.status_code == 200
    assert r.json()["title"] == "Aliens"
    r2 = client.get("/api/v1/movies/9999")
    assert r2.status_code == 404


def test_recommendations_similar_excludes_input(client):
    r = client.get("/api/v1/recommendations/similar/10?top_k=5")
    assert r.status_code == 200
    ids = [x["movie"]["movie_id"] for x in r.json()["items"]]
    assert 10 not in ids


def test_rating_range_validation(client):
    r = client.post("/api/v1/ratings", json={"user_id": 1, "movie_id": 10, "value": 6})
    assert r.status_code == 422


def test_rating_persisted_and_returned(client):
    r = client.post("/api/v1/ratings", json={"user_id": 1, "movie_id": 10, "value": 4})
    assert r.status_code == 201
    r2 = client.get("/api/v1/users/1/ratings")
    assert r2.status_code == 200
    assert any(x["movie_id"] == 10 and x["value"] == 4 for x in r2.json())


def test_favorites_add_remove(client):
    r = client.post("/api/v1/users/1/favorites", json={"movie_id": 11})
    assert r.status_code == 201
    r2 = client.get("/api/v1/users/1/favorites")
    assert any(f["movie_id"] == 11 for f in r2.json())
    r3 = client.delete("/api/v1/users/1/favorites/11")
    assert r3.status_code == 204
    r4 = client.get("/api/v1/users/1/favorites")
    assert all(f["movie_id"] != 11 for f in r4.json())


def test_duplicate_favorite_is_idempotent(client):
    a = client.post("/api/v1/users/1/favorites", json={"movie_id": 12})
    b = client.post("/api/v1/users/1/favorites", json={"movie_id": 12})
    assert a.status_code == 201 and b.status_code == 201
    lst = client.get("/api/v1/users/1/favorites").json()
    assert sum(1 for x in lst if x["movie_id"] == 12) == 1


def test_preferences_update_and_read(client):
    r = client.put("/api/v1/users/1/preferences",
                   json={"genres": ["Action", "Sci-Fi"], "seed_movie_ids": [10, 12]})
    assert r.status_code == 200
    body = r.json()
    assert set(body["genres"]) == {"Action", "Sci-Fi"}
    assert 10 in body["seed_movie_ids"]


def test_analytics_model_comparison_missing_ok(client, tmp_path, monkeypatch):
    # If evaluation.json is not present we expect a documented 503, not a fake 200.
    from app.core.config import settings
    monkeypatch.setattr(settings, "artifacts_dir", tmp_path)
    r = client.get("/api/v1/analytics/model-comparison")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "model_not_trained"
