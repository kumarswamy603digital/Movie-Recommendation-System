# API Reference

Base path: **`/api/v1`**. All timestamps are ISO-8601 UTC. Errors follow a
single envelope. Live OpenAPI at `http://localhost:8000/docs` (Swagger UI)
and `http://localhost:8000/redoc` once the server is running.

## Envelope

Success → 200/201/204, JSON body per response schema.

Error → JSON:

```json
{
  "error": {
    "code": "not_found",
    "message": "Movie 99999 not found.",
    "details": null
  }
}
```

Codes: `not_found` (404), `validation_error` (422), `conflict` (409),
`model_not_trained` (503), `integration_unavailable` (503). FastAPI's own
422 body (`{"detail": [...]}`) is preserved for request-level validation
errors.

Every response includes:

| Header | Meaning |
|--------|---------|
| `x-correlation-id` | Echoes the request's `x-correlation-id` header or generates a uuid4 |
| `x-process-time-ms` | Server-side processing time in milliseconds |

## System

### `GET /api/v1/health`

Liveness probe. No dependencies.

```json
{ "status": "ok", "version": "1.0.0" }
```

### `GET /api/v1/ready`

Readiness probe. Loads the registry if needed.

```json
{
  "status": "ok",
  "readiness": {
    "api_process": true,
    "database": true,
    "catalogue_loaded": true,
    "popularity_ready": true,
    "content_ready": true,
    "collaborative_ready": true,
    "hybrid_ready": true,
    "tmdb_enabled": false
  }
}
```

Returns `status: "degraded"` if catalogue is empty (i.e. preprocess has not
been run).

## Movies

### `GET /api/v1/movies`

Paginated catalogue list.

Query:
- `q` (str, max 120) — substring search on title
- `genre` (str, max 40) — exact genre name (case-insensitive)
- `year_min`, `year_max` (int, 1900..2100)
- `page` (int ≥ 1, default 1)
- `page_size` (int 1..100, default 25)
- `sort` — one of `popularity | rating | title | year` (default `popularity`)

Response `MoviePage`:

```json
{
  "items": [
    {
      "movie_id": 285,
      "title": "Good, The Bad and The Ugly, The",
      "release_year": 1966,
      "genres": ["Western"],
      "tmdb_id": null,
      "poster_url": null,
      "overview": null,
      "rating_count": 307,
      "mean_rating": 4.16
    }
  ],
  "total": 1682,
  "page": 1,
  "page_size": 25
}
```

### `GET /api/v1/movies/search`

Shorthand — same shape as `/movies`, `q` required.

### `GET /api/v1/movies/{movie_id}`

Single `MovieWithStats`. 404 if unknown. When TMDB is enabled and the movie
has a `tmdb_id`, the response's `poster_url` is enriched.

### `GET /api/v1/genres`

`Genre[]`:

```json
[{ "name": "Action", "movie_count": 167 }, ...]
```

## Recommendations

All return `RecommendationList`:

```json
{
  "strategy": "hybrid",
  "user_id": 42,
  "based_on_movie_id": null,
  "personalized": true,
  "notes": ["Hybrid blend (pop=0.20, content=0.35, cf=0.45)."],
  "items": [
    {
      "movie": { "...": "MovieWithStats fields" },
      "score": 0.712,
      "reasons": [
        { "kind": "content", "text": "Matches 2 of your seed genres: Sci-Fi, Thriller" },
        { "kind": "collaborative", "text": "Loved by users with taste similar to yours" }
      ],
      "component_scores": { "popularity": 0.42, "content": 0.62, "cf": 0.90 }
    }
  ]
}
```

### `GET /api/v1/recommendations/popular`

Query `user_id` (optional; excludes already-rated titles), `top_k` (1..100,
default 20). Always safe: returns `[]` if popularity not fitted.

### `GET /api/v1/recommendations/similar/{movie_id}`

Content-based neighbours. Query `top_k` (1..50, default 20).

### `GET /api/v1/recommendations/users/{user_id}`

Personalised list. Query `strategy` — one of `hybrid | popularity | content
| collaborative` (default `hybrid`), `top_k`.

### `POST /api/v1/recommendations`

Body:

```json
{
  "user_id": 42,
  "strategy": "hybrid",
  "top_k": 20,
  "genres": ["Sci-Fi", "Thriller"],
  "year_min": 1980,
  "year_max": 2005,
  "exclude_rated": true
}
```

Same response as GET. Post-filters applied **after** ranking, so top_k is
the pre-filter K.

### `GET /api/v1/recommendations/explanations/{movie_id}`

Query `user_id` (optional). Returns:

```json
{
  "movie_id": 50,
  "user_id": 42,
  "personalized": true,
  "reasons": [{ "kind": "hybrid", "text": "..." }]
}
```

Reasons are only emitted when the underlying signal is real (see
[Architecture](architecture.md) — Failure modes).

## Users

### `POST /api/v1/ratings`

Body `{ user_id, movie_id, value }`, `value ∈ [1..5]`. 201 on success.
Upserts on (user_id, movie_id).

### `GET /api/v1/users/{user_id}/ratings`

`RatingOut[]` ordered by `updated_at` desc.

### `POST /api/v1/users/{user_id}/favorites`

Body `{ movie_id }`. Idempotent — returns existing row if already saved.

### `DELETE /api/v1/users/{user_id}/favorites/{movie_id}`

204 whether the row existed or not.

### `GET /api/v1/users/{user_id}/favorites`

`FavoriteOut[]`.

### `PUT /api/v1/users/{user_id}/preferences`

Body `{ genres: [str], seed_movie_ids: [int] }`. `genres` are normalised to
a sorted set. Response `PreferenceOut` includes `updated_at`.

### `GET /api/v1/users/{user_id}/preferences`

If none saved yet, returns an empty shape (`genres: [], seed_movie_ids: []`)
rather than 404 — keeps the frontend onboarding form simple.

## Analytics

### `GET /api/v1/analytics/overview`

```json
{
  "dataset": {
    "dataset_version": "ml-100k",
    "n_users": 943,
    "n_movies": 1682,
    "n_ratings": 100000,
    "n_genres": 18,
    "missing_values": {"release_year": 2, "genres": 2},
    "processed_at": "2026-10-27T…"
  },
  "model_version": "2026-10-27T00:12:34Z",
  "n_fitted_users": 943,
  "n_catalog_movies": 1682
}
```

### `GET /api/v1/analytics/model-comparison`

```json
{
  "protocol": "temporal-last5-min20-rel4",
  "top_k": 10,
  "metrics": [
    {
      "model": "collaborative",
      "evaluation_date": "2026-10-27",
      "top_k": 10,
      "precision_at_k": 0.04793,
      "recall_at_k": 0.15217,
      "ndcg_at_k": 0.11612,
      "coverage": 0.12961,
      "rmse": 1.073,
      "mae": 0.841,
      "notes": "820 users evaluated"
    },
    ...
  ]
}
```

Returns **503 `model_not_trained`** with an actionable message when
`artifacts/evaluation.json` is missing. No fallback zeros.

## Root aliases

`GET /health` (no version prefix) mirrors `/api/v1/health` for load
balancers that don't respect path rewrites.

## CORS

Configured via `CORS_ORIGINS` (comma-separated). Defaults to
`["http://localhost:5173"]` for Vite dev server.
