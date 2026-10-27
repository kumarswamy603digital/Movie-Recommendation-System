"""Shared pytest fixtures: an in-memory SQLite DB + a minimal fitted registry."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure `app` importable when running under pytest from backend/.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Force SQLite file DB in a temp location so tests never touch developer state.
_TMP = tempfile.NamedTemporaryFile(prefix="app_", suffix=".sqlite3", delete=False)
_TMP.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.name}"

from app.db.base import Base, get_db  # noqa: E402
from app.models.db_models import *  # noqa: E402, F403


@pytest.fixture(scope="function")
def db_session():
    eng = create_engine(f"sqlite:///{_TMP.name}", future=True)
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def tiny_ratings():
    return pd.DataFrame({
        "user_id":  [1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 5, 5],
        "movie_id": [10, 11, 12, 10, 11, 13, 12, 13, 14, 10, 11, 14],
        "rating":   [5.0, 4.0, 3.0, 4.0, 5.0, 2.0, 5.0, 3.0, 4.0, 3.0, 5.0, 5.0],
    })


@pytest.fixture
def tiny_movies():
    return pd.DataFrame({
        "movie_id": [10, 11, 12, 13, 14],
        "title": ["Aliens", "Alien 3", "Predator", "Star Wars", "Die Hard"],
        "release_year": [1986, 1992, 1987, 1977, 1988],
        "genres": ["Action|Sci-Fi", "Action|Horror", "Action|Sci-Fi",
                    "Action|Sci-Fi", "Action|Thriller"],
    })
