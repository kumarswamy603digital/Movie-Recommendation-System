"""Unit tests for the four recommender strategies using small fixtures."""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.recommender.collaborative import CollaborativeRecommender
from app.recommender.content_based import ContentBasedRecommender
from app.recommender.hybrid import HybridRecommender, HybridWeights
from app.recommender.popularity import PopularityRecommender


# ---------------- Popularity ----------------

def test_popularity_bayesian_prefers_support_over_5star_few_votes(tiny_ratings):
    # Add a 5.0-rated item with one vote; should NOT outrank well-supported items.
    tiny = pd.concat([
        tiny_ratings,
        pd.DataFrame({"user_id": [9], "movie_id": [99], "rating": [5.0]}),
    ], ignore_index=True)
    pop = PopularityRecommender.fit(tiny, min_ratings=2)
    top = pop.global_top(top_k=5)
    ids = [t.movie_id for t in top]
    assert 99 not in ids  # suppressed by min_ratings
    assert 10 in ids      # 4 votes -> wins


def test_popularity_excludes_specified_movies(tiny_ratings):
    pop = PopularityRecommender.fit(tiny_ratings, min_ratings=1)
    out = pop.global_top(top_k=5, exclude_movie_ids={10, 11})
    ids = {t.movie_id for t in out}
    assert 10 not in ids and 11 not in ids


def test_popularity_stats_returns_mean_and_count(tiny_ratings):
    pop = PopularityRecommender.fit(tiny_ratings, min_ratings=1)
    s = pop.stats(10)
    # Movie 10 is rated by users 1, 2, 4 -> count == 3.
    assert s is not None and s["rating_count"] == 3


# ---------------- Content-based ----------------

def test_content_similar_excludes_input(tiny_movies):
    cb = ContentBasedRecommender.fit(tiny_movies)
    sim = cb.similar_to_movie(10, top_k=5)
    ids = [s.movie_id for s in sim]
    assert 10 not in ids


def test_content_unknown_movie_returns_empty(tiny_movies):
    cb = ContentBasedRecommender.fit(tiny_movies)
    assert cb.similar_to_movie(9999, top_k=5) == []


def test_content_action_sci_fi_neighbours(tiny_movies):
    cb = ContentBasedRecommender.fit(tiny_movies)
    sim = cb.similar_to_movie(10, top_k=3)  # Aliens (Action|Sci-Fi)
    ids = [s.movie_id for s in sim]
    # Predator (12) and Star Wars (13) share Action|Sci-Fi; Alien 3 (11) shares only Action.
    assert 12 in ids[:2]
    assert 13 in ids[:2]


# ---------------- Collaborative ----------------

def test_cf_user_with_history_gets_recommendations(tiny_ratings):
    cf = CollaborativeRecommender.fit(tiny_ratings, svd_components=0)
    assert cf.user_has_history(1)
    ranked = cf.top_for_user(1, tiny_ratings[tiny_ratings.user_id == 1].set_index("movie_id")["rating"], {10, 11, 12}, top_k=5)
    assert isinstance(ranked, list)


def test_cf_cold_start_user_returns_empty(tiny_ratings):
    cf = CollaborativeRecommender.fit(tiny_ratings, svd_components=0)
    assert not cf.user_has_history(9999)
    assert cf.top_for_user(9999, None, set(), 5) == []


def test_cf_predict_rating_in_range(tiny_ratings):
    cf = CollaborativeRecommender.fit(tiny_ratings, svd_components=0)
    p = cf.predict_rating(1, 10)
    assert p is not None and 1.0 <= p <= 5.0


# ---------------- Hybrid ----------------

def test_hybrid_falls_back_to_popularity_when_no_history(tiny_ratings, tiny_movies):
    pop = PopularityRecommender.fit(tiny_ratings, min_ratings=1)
    cb = ContentBasedRecommender.fit(tiny_movies)
    cf = CollaborativeRecommender.fit(tiny_ratings, svd_components=0)
    hy = HybridRecommender(pop, cb, cf)
    out = hy.rank(user_id=9999, ratings_by_user=None, exclude_movie_ids=set(), top_k=5)
    # Unknown user without seeds -> blended from popularity only.
    assert len(out) > 0


def test_hybrid_deterministic(tiny_ratings, tiny_movies):
    pop = PopularityRecommender.fit(tiny_ratings, min_ratings=1)
    cb = ContentBasedRecommender.fit(tiny_movies)
    cf = CollaborativeRecommender.fit(tiny_ratings, svd_components=0)
    hy = HybridRecommender(pop, cb, cf, weights=HybridWeights(0.2, 0.35, 0.45))
    a = hy.rank(1, tiny_ratings[tiny_ratings.user_id == 1].set_index("movie_id")["rating"], set(), 5, seed_movie_ids=[10, 11])
    b = hy.rank(1, tiny_ratings[tiny_ratings.user_id == 1].set_index("movie_id")["rating"], set(), 5, seed_movie_ids=[10, 11])
    assert [x.movie_id for x in a] == [x.movie_id for x in b]


def test_hybrid_weights_renormalise():
    w = HybridWeights(1, 1, 2).renormalized()
    assert abs(w.popularity + w.content + w.collaborative - 1.0) < 1e-9
