# Data Dictionary

Covers both (a) the raw MovieLens 100K files the pipeline consumes and
(b) the SQLite tables the API persists.

## Raw dataset — MovieLens 100K

Location after `scripts/download_dataset.py`: `backend/data/ml-100k/`.

### `u.data` — ratings

Tab-separated, **no header**. 100,000 rows.

| Column | Type | Notes |
|--------|------|-------|
| user_id | int | 1..943 |
| movie_id | int | 1..1682 |
| rating | int | 1..5, integer (no halves) |
| timestamp | int | Unix seconds; used as an ordering proxy (no true event time) |

Uniqueness: (user_id, movie_id). `preprocess_data.py` keeps the last row
per pair if duplicates are ever present (defensive — the shipped file has
none).

### `u.item` — movies

Pipe-separated (`|`), **no header**. 1,682 rows.

| Column | Type | Notes |
|--------|------|-------|
| movie_id | int | 1..1682 |
| title | str | Often includes `(YYYY)` — parsed out into `release_year` |
| release_date | str or empty | `DD-MMM-YY` or missing (~2 rows) |
| imdb_url | str or empty | Not currently used |
| unknown | 0/1 | Genre indicator — treated as "no genre" and skipped |
| Action..Children's | 0/1 × 18 | Multi-hot genres; converted to a `|`-joined string |

### `u.genre`

Pipe-separated. 19 rows. `name|id`. `Unknown` (id 0) is dropped during
preprocessing.

### `u.user` — users (optional in current pipeline)

Pipe-separated. 943 rows. `user_id|age|gender|occupation|zip`. Not used at
runtime; the demo assumes user_id ∈ 1..943.

## Processed CSV — `backend/data/processed/`

Written by `scripts/preprocess_data.py`. Loaded by the recommender registry.

### `movies.csv`

| Column | Type | Notes |
|--------|------|-------|
| movie_id | int64 | PK |
| title | str | `(YYYY)` suffix stripped |
| release_year | int16 or null | 2 rows are null (missing release_date in `u.item`) |
| genres | str | Pipe-joined, e.g. `Action\|Crime\|Thriller`. Empty for 2 rows. |
| imdb_url | str or null | |

### `ratings.csv`

| Column | Type | Notes |
|--------|------|-------|
| user_id | int32 | |
| movie_id | int32 | |
| value | int8 | 1..5 enforced |
| timestamp | int64 | Unix seconds; ordering key |

### `summary.json`

```json
{
  "dataset_version": "ml-100k",
  "n_users": 943,
  "n_movies": 1682,
  "n_ratings": 100000,
  "n_genres": 18,
  "missing_values": {"movies.release_year": 2, "movies.genres": 2},
  "processed_at": "2026-10-27T00:00:00Z"
}
```

## Artifacts — `backend/artifacts/`

Written by `scripts/train_models.py` and `scripts/evaluate_models.py`. All
git-ignored.

| File | Contents |
|------|----------|
| `popularity.joblib` | `PopularityTable`: movie_id order, weighted-score array, count, mean |
| `content.joblib` | `TfidfVectorizer` + `csr_matrix` of shape (n_movies, vocab) |
| `collaborative.joblib` | Sparse R, sparsified item-item cosine matrix, user/item means, `TruncatedSVD`, latent user vectors |
| `evaluation.json` | Protocol metadata + per-model metrics rows |
| `model_version.json` | `{version, dataset, weights, timing}` — bumped each training run |

## SQLite tables — created on startup via `Base.metadata.create_all`

DB file defaults to `backend/app.db` (`DATABASE_URL` env-configurable).

### `users`

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK autoincrement |
| email | str(255) | unique, nullable |
| display_name | str(120) | nullable |
| is_demo | bool | default true |
| created_at | datetime | default `utcnow` |

Holds **only** demo / locally-created accounts. No authentication.

### `ratings`

User-authored ratings that override / extend the dataset for a session.

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK |
| user_id | int | FK → users.id, indexed |
| movie_id | int | indexed (references dataset, not a FK — movies are file-backed) |
| value | int | CheckConstraint 1..5 |
| updated_at | datetime | |
| | | UniqueConstraint(user_id, movie_id) |

### `favorites`

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK |
| user_id | int | FK |
| movie_id | int | |
| created_at | datetime | |
| | | UniqueConstraint(user_id, movie_id) |

Add is idempotent via ON CONFLICT.

### `preferences`

| Column | Type | Constraints |
|--------|------|-------------|
| id | int | PK |
| user_id | int | FK, Unique |
| genres | JSON | list[str], normalised sorted set |
| seed_movie_ids | JSON | list[int] |
| updated_at | datetime | |

### `recommendation_feedback`

Reserved for future implicit-signal capture (click / dismiss / rating from
a recommendation card). Currently written by nothing; the table exists.

| Column | Type |
|--------|------|
| id | int PK |
| user_id | int FK |
| movie_id | int |
| signal | str |
| created_at | datetime |
| | UniqueConstraint(user_id, movie_id) |

## Field mapping: raw → processed → wire

```
u.item.title        → movies.csv.title         → Movie.title
u.item.(parse YYYY) → movies.csv.release_year  → Movie.release_year
u.item.genre flags  → movies.csv.genres (split)|→ Movie.genres[]
u.data.rating       → ratings.csv.value        → (used in training only)
u.data.user_id      → ratings.csv.user_id      → RatingOut.user_id
processed summary   → summary.json             → DatasetSummary
```

## Retention / PII

Nothing that would count as PII is stored. `user_id` in the SQLite tables
is an internal integer; `email` is nullable and unused in the demo flow.
The MovieLens dataset is public, de-identified, and licensed for research
use.
