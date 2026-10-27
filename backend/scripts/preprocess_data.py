"""Preprocess MovieLens into a compact, stable CSV layout.

Reads raw MovieLens files (ml-100k by default), normalizes genres, parses
years out of titles, deduplicates ratings, validates rating range, and writes:
    data/processed/movies.csv    (movie_id, title, release_year, genres)
    data/processed/ratings.csv   (user_id, movie_id, rating)
    data/processed/summary.json  (counts + missing values + dataset version)

Usage:
    python -m scripts.preprocess_data
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings  # noqa: E402


YEAR_RE = re.compile(r"\((\d{4})\)\s*$")


def _load_ml100k(base: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ratings = pd.read_csv(
        base / "u.data", sep="\t", header=None,
        names=["user_id", "movie_id", "rating", "timestamp"],
        encoding="latin-1",
    )
    movie_cols = ["movie_id", "title", "release_date", "video_release_date", "imdb_url"] + \
                 [f"g_{i}" for i in range(19)] + ["unknown_genre"]
    items = pd.read_csv(
        base / "u.item", sep="|", header=None, names=movie_cols,
        encoding="latin-1", on_bad_lines="skip",
    )
    return ratings, items


def _genres_from_items_ml100k(items: pd.DataFrame) -> pd.DataFrame:
    genre_cols = [c for c in items.columns if c.startswith("g_")]
    genre_map = pd.read_csv(
        Path(settings.data_dir) / settings.movielens_dataset / "u.genre",
        sep="|", header=None, names=["name", "id"], encoding="latin-1",
    )
    id_to_name = {int(r.id): str(r.name) for r in genre_map.itertuples() if str(r.name) != "unknown"}
    def row_genres(row):
        names = [id_to_name.get(int(c[2:]), "") for c in genre_cols if int(row[c] or 0) == 1]
        return "|".join([n for n in names if n])
    items["genres"] = items.apply(row_genres, axis=1)
    return items


def _year_from_title(title: str) -> int | None:
    m = YEAR_RE.search(str(title))
    return int(m.group(1)) if m else None


def _normalize_movies_ml100k(items: pd.DataFrame) -> pd.DataFrame:
    items = _genres_from_items_ml100k(items)
    df = pd.DataFrame({
        "movie_id": items["movie_id"].astype(int),
        "title": items["title"].astype(str).map(lambda t: YEAR_RE.sub("", t).strip()),
        "release_year": items["title"].map(_year_from_title),
        "genres": items["genres"].astype(str),
    })
    return df.drop_duplicates(subset=["movie_id"]).reset_index(drop=True)


def _clean_ratings(r: pd.DataFrame) -> pd.DataFrame:
    before = len(r)
    r = r.drop_duplicates(subset=["user_id", "movie_id"], keep="last")
    r = r[(r["rating"] >= 1) & (r["rating"] <= 5)]
    after = len(r)
    print(f"Ratings: {before:,} -> {after:,} after dedup + range filter.")
    return r[["user_id", "movie_id", "rating"]].astype({"user_id": "int64", "movie_id": "int64"})


def main() -> int:
    base = Path(settings.data_dir) / settings.movielens_dataset
    if not base.exists():
        print(f"Dataset directory missing: {base}. Run scripts.download_dataset first.", file=sys.stderr)
        return 2

    if settings.movielens_dataset == "ml-100k":
        ratings_raw, items = _load_ml100k(base)
        movies = _normalize_movies_ml100k(items)
    else:
        print(f"Only ml-100k is implemented here. Add loader for {settings.movielens_dataset}.", file=sys.stderr)
        return 4

    ratings = _clean_ratings(ratings_raw)

    # Keep only ratings that reference a known movie_id.
    known = set(movies["movie_id"].tolist())
    ratings = ratings[ratings["movie_id"].isin(known)]

    out = Path(settings.processed_dir)
    out.mkdir(parents=True, exist_ok=True)
    movies.to_csv(out / "movies.csv", index=False)
    ratings.to_csv(out / "ratings.csv", index=False)

    missing = {
        "movies.release_year": int(movies["release_year"].isna().sum()),
        "movies.genres_empty": int((movies["genres"].fillna("") == "").sum()),
        "ratings.duplicates_removed": int(len(ratings_raw) - len(ratings)),
    }
    summary = {
        "dataset_version": settings.movielens_dataset,
        "n_users": int(ratings["user_id"].nunique()),
        "n_movies": int(movies["movie_id"].nunique()),
        "n_ratings": int(len(ratings)),
        "n_genres": len({g for row in movies["genres"] for g in str(row).split("|") if g}),
        "missing_values": missing,
        "attribution": "GroupLens Research. https://grouplens.org/datasets/movielens/",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote processed data to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
