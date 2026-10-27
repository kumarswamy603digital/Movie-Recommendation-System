# PROJECT_STATUS.md — Movie Recommendation System (PROJECT2)

Living status log. Current date: 2026-10-27.

## Verified environment
- Python: 3.14.7. Venv at `../backend/.venv` shared for development.
- ML stack installed and imported successfully: pandas 2.3.3, numpy 2.5.4,
  scikit-learn 1.9.1, scipy 1.18.1, joblib 1.6.0.
- Web / DB stack: FastAPI 0.162, SQLAlchemy 2.0.41, Alembic 1.16.4,
  pydantic 2.14.1, uvicorn 0.54, httpx 0.28.
- Node.js / npm: NOT installed on the machine (same blocker as the previous
  project). Frontend code is authored but cannot be executed here.
- Docker: NOT installed. Compose file + Dockerfile are provided but not
  exercised on this machine.
- Dataset: MovieLens 100K downloaded via
  `https://files.grouplens.org/datasets/movielens/ml-100k.zip` (4,924,029
  bytes → 21 extracted files). Located at `backend/data/ml-100k/`.

## Pipeline actually executed
Run from `PROJECT2/backend`:

- `python -m scripts.download_dataset` (idempotent — files already present).
- `python -m scripts.preprocess_data`
  - Ratings 100,000 → 100,000 after dedup + 1..5 range filter.
  - Movies: 1,682 rows, 2 missing release years, 2 empty genre fields.
- `python -m scripts.train_models`
  - Popularity (Bayesian weighted rating), Content-based (TF-IDF 2,089
    vocab + cosine, sparse), Collaborative (item-item CF on sparse
    user×item matrix; TruncatedSVD fitted on centered ratings).
  - Saved to `backend/artifacts/{popularity,content,collaborative}.joblib`.
- `python -m scripts.evaluate_models` — real metrics:

  | Strategy        | Precision@10 | Recall@10 | NDCG@10 | Coverage | RMSE  | MAE   |
  |-----------------|--------------|-----------|---------|----------|-------|-------|
  | Popularity      | 0.02317      | 0.06762   | 0.04758 | 0.04221  | —     | —     |
  | Content-based   | 0.00622      | 0.01880   | 0.01376 | 0.25684  | —     | —     |
  | Collaborative   | 0.04793      | 0.15217   | 0.11612 | 0.12961  | 1.073 | 0.841 |
  | Hybrid (0.2/0.35/0.45) | 0.04146 | 0.12754 | 0.09487 | 0.15101 | — | — |

  Protocol: per-user temporal last-5 holdout, min 20 train ratings per
  user; relevant = rating >= 4; models fit only on TRAIN. Evaluated on
  820 users.

  **Honest observation:** the current hybrid configuration does NOT beat
  pure collaborative on Precision@10 / Recall@10 / NDCG@10 on ML-100K.
  Collaborative is the strongest top-N ranker here. Content-based
  contributes the widest coverage (0.25684) but the weakest precision.
  The hybrid sits between them. This is reported as measured, not
  smoothed over.

## Test suite
`python -m pytest` → **24 passed** (5.24 s, 3 warnings).
- 12 unit tests over popularity / content / collaborative / hybrid.
- 12 integration tests over the FastAPI endpoints (health, ready, list,
  filter by genre, get, similar, rating validation, persistence, favorites
  idempotency, preferences, analytics missing-evaluation 503).

## Backend layout (all code present and executed)
```
backend/
  app/
    core/         config.py, logging.py, exceptions.py
    db/           base.py (engine + SessionLocal + get_db + init_db)
    models/       db_models.py (User, Rating, Favorite, Preference, RecommendationFeedback)
    schemas/      schemas.py (all Pydantic v2)
    repositories/ repository.py (thin DB helpers)
    services/     domain.py (movie listing, recommendations, user interactions)
    recommender/  base.py, popularity.py, content_based.py,
                  collaborative.py, hybrid.py, explanations.py, registry.py
    integrations/ tmdb.py (optional; gracefully no-ops when no key)
    api/routes/   all_routes.py (system, movies, genres, recommendations,
                  users, analytics — all under /api/v1)
    main.py       FastAPI bootstrap (CORS, correlation-id middleware,
                  exception handlers, lifespan loads registry)
  scripts/        download_dataset.py, preprocess_data.py,
                  train_models.py, evaluate_models.py
  tests/          conftest.py, unit/test_recommenders.py,
                  integration/test_api.py
  data/           (git-ignored) ml-100k/, processed/
  artifacts/      (git-ignored) *.joblib, evaluation.json, model_version.json
  requirements.txt
  pytest.ini
  .env.example
```

## Frontend layout — code complete, execution blocked
Stack: React 18 + Vite 5 + TypeScript + Tailwind 3 + React Router 6 +
TanStack Query 5 + Recharts + Vitest + RTL. Dark cinematic theme.

```
frontend/
  src/
    api/          client.ts (typed fetch), queries.ts (TanStack hooks)
    components/   Layout.tsx, ui.tsx (LoadingSkeleton / EmptyState /
                  ErrorState / Pagination / GenreFilter / SearchBar),
                  movie.tsx (MovieCard / RecommendationCard / Grids /
                  GenreChips / ReasonList), RatingControl.tsx
    hooks/        useUser.ts (localStorage id), theme inside same file
    pages/        Home, Discover, MovieDetails, Personalized, Onboarding,
                  Favorites, MyRatings, ModelInsights, About
    test/         setup.ts, mockFetch.ts, app.test.tsx (4 smoke tests)
    types/        api.ts — mirrors backend Pydantic schemas exactly
    App.tsx, main.tsx, index.css, vite-env.d.ts
  package.json, tsconfig.json, vite.config.ts, tailwind.config.js,
  postcss.config.js, index.html, .env.example, README.md
```

- Cannot execute `npm install`, `npm run dev`, or `npm run test:run` on
  this machine because Node.js is not installed (admin-required
  `winget install OpenJS.NodeJS.LTS` is the same blocker documented for
  the previous project).
- Every type in `frontend/src/types/api.ts` was aligned field-by-field
  with the running backend by inspecting
  `backend/app/schemas/schemas.py` and `backend/app/api/routes/all_routes.py`.
- The frontend never fabricates data — if `/analytics/model-comparison`
  returns 503, the ModelInsights page honestly shows the error message
  from the backend.

## Documentation

Complete:
- `README.md` (root): quickstart, architecture, real metrics, limitations,
  API surface, repo layout, license
- `frontend/README.md`: dev / build / test / page-by-page tour
- `docs/architecture.md`: Mermaid system + sequence diagrams, module
  responsibility table, design decisions, failure modes, extension points
- `docs/data_dictionary.md`: raw MovieLens fields, processed CSVs,
  artifacts, SQLite tables, field mapping, PII notes
- `docs/model_evaluation.md`: protocol, metric definitions, real numbers,
  honest interpretation, tuning suggestions, reproduction steps
- `docs/api_reference.md`: all endpoints, request/response shapes, error
  envelope, CORS
- `docs/deployment.md`: local + Docker + cloud topology, config matrix,
  migrations, operational checklist, "not ready" list
- `docs/demo_script.md`: 10-minute walkthrough with talking points and
  "what NOT to say" section

## Docker

- `Dockerfile` (backend image): python:3.12-slim, installs requirements,
  runs pipeline inside the build for offline-safe startup, exposes 8000,
  HEALTHCHECK against `/api/v1/health`.
- `docker-compose.yml`: backend + frontend services, `appdata` volume for
  SQLite + artifacts, env passthrough for CORS + TMDB + hybrid weights.
- **Not exercised on this machine — Docker is not installed.**

## Remaining work / known limitations
- Frontend execution verification (blocked on Node install).
- Docker build verification (blocked on Docker install).
- Alembic migrations: `Base.metadata.create_all()` currently handles
  table creation on first run. Alembic is installed but not wired in —
  see `docs/deployment.md` for production steps.
- Authentication: **local demo mode only** — no real user accounts. This
  is intentional and honest; production hardening is documented.
- SVD-based rating prediction is fit but not used for ranking; the CF
  ranker uses item-item cosine similarity for transparency.
- Hybrid weights are set by env defaults (0.20 / 0.35 / 0.45). They can
  be tuned; the current blend does not beat pure collaborative on ML-100K
  top-N ranking, which is reported as measured.

## What a developer can run right now (verified)
```powershell
# 1. Ensure dependencies:
cd PROJECT2/backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. Pipeline (dataset already downloaded on this machine, otherwise):
.\.venv\Scripts\python.exe -m scripts.download_dataset
.\.venv\Scripts\python.exe -m scripts.preprocess_data
.\.venv\Scripts\python.exe -m scripts.train_models
.\.venv\Scripts\python.exe -m scripts.evaluate_models

# 3. Tests:
.\.venv\Scripts\python.exe -m pytest -q   # 24 passed

# 4. Start API:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
# -> http://localhost:8000/api/v1/health  (openapi at /docs)
```

Frontend commands are documented in `frontend/README.md` and require
Node.js to be installed first. Docker commands are documented in
`docs/deployment.md` and require Docker Desktop first.
