# Movie Recommendation System (PROJECT2)

Full-stack ML project — FastAPI + React + a reproducible offline pipeline on
the MovieLens 100K dataset. Four distinct recommender strategies (popularity,
content-based, item-item collaborative, weighted hybrid) behind one interface,
with honest explanations and an offline evaluation that reports the real
numbers, including the ones that are unflattering.

> **Note on status**: this project has been **built and executed locally**
> on Windows. The backend pipeline has produced real metrics (Precision@10,
> Recall@10, NDCG@10, Coverage, RMSE, MAE) on 820 users of MovieLens 100K.
> All 24 backend tests pass. Frontend code is authored against the actual
> running API but cannot be executed on this machine (no Node.js). Docker
> is not installed on this machine either — the compose file is provided but
> has not been run. Nothing in this project has been deployed.

## Table of contents

- [What's inside](#whats-inside)
- [Architecture at a glance](#architecture-at-a-glance)
- [Quickstart](#quickstart)
- [The four recommenders](#the-four-recommenders)
- [Real evaluation numbers](#real-evaluation-numbers)
- [Honest limitations](#honest-limitations)
- [Testing](#testing)
- [API surface](#api-surface)
- [Documentation](#documentation)
- [Repo layout](#repo-layout)

## What's inside

| Layer | Tech | Purpose |
|-------|------|---------|
| Frontend | React 18 + Vite + TS + Tailwind + TanStack Query + Recharts | Dark-cinematic SPA, 9 pages |
| Backend | FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic (installed) | REST API under `/api/v1`, correlation-id middleware, structured logging |
| ML | scikit-learn, numpy, scipy, pandas, joblib | TF-IDF, cosine similarity, item-item CF, TruncatedSVD, weighted hybrid |
| Pipeline | 4 idempotent Python scripts | Download → Preprocess → Train → Evaluate |
| Persistence | SQLite (dev), Postgres-compatible (schema) | User ratings, favorites, preferences |
| Integration | TMDB v3 (optional) | Poster + overview enrichment when `TMDB_API_KEY` is set |

## Architecture at a glance

```
 Browser SPA (Vite dev :5173)
        │  fetch
        ▼
 FastAPI (:8000)  ───►  services/domain.py
        │                    │
        │                    ├──►  recommender.registry (process-wide singleton)
        │                    │        ├── PopularityRecommender   (Bayesian WR)
        │                    │        ├── ContentBasedRecommender (TF-IDF + cosine)
        │                    │        ├── CollaborativeRecommender(item-item CF + SVD)
        │                    │        └── HybridRecommender       (normalised blend)
        │                    │
        │                    └──►  repositories/repository.py
        │                              │
        ▼                              ▼
   SQLite / Postgres              artifacts/*.joblib
                              data/processed/*.csv
```

Full diagram + request lifecycle + failure modes in
[docs/architecture.md](docs/architecture.md).

## Quickstart

Two terminals, PowerShell on Windows.

**Terminal 1 — backend**

```powershell
cd PROJECT2\backend

# 1. venv (or reuse an existing one — see note below)
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# 2. pipeline
.\.venv\Scripts\python.exe -m scripts.download_dataset
.\.venv\Scripts\python.exe -m scripts.preprocess_data
.\.venv\Scripts\python.exe -m scripts.train_models
.\.venv\Scripts\python.exe -m scripts.evaluate_models

# 3. tests — should say "24 passed"
.\.venv\Scripts\python.exe -m pytest -q

# 4. serve
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
# API: http://localhost:8000/api/v1/health
# Docs: http://localhost:8000/docs
```

**Terminal 2 — frontend** (requires Node.js ≥ 20)

```powershell
cd PROJECT2\frontend
npm install
npm run dev
# Open: http://localhost:5173
```

**Docker** (if installed):

```powershell
cd PROJECT2
docker compose up --build
```

## The four recommenders

| Strategy | Core method | Cold-start behaviour | Best for |
|----------|-------------|----------------------|----------|
| **Popularity** | Bayesian Weighted Rating: `WR = (v/(v+m))·R + (m/(v+m))·C`, suppress items with count < 20 | Never empty | Sane baseline / fallback |
| **Content-based** | TF-IDF over genres + title, cosine row-to-row on a sparse matrix | Needs ≥1 seed movie | Wide catalogue coverage |
| **Collaborative** | Item-item cosine on the sparse user×item matrix, sparsified to top-200 neighbours/row; TruncatedSVD on centered user matrix for latent factors; mean-biased neighbourhood rating prediction for RMSE/MAE | Returns `[]` for unseen users | Highest top-N precision |
| **Hybrid** | Independent min-max normalisation of each component, weighted blend (default `0.20 / 0.35 / 0.45`), drop-and-renormalise on missing components, `np.lexsort` for deterministic ties | Falls back to popularity | Coverage + graceful degradation |

Every recommender shares the `Recommender` interface (`base.py`) and the
same `Scored(movie_id, score, components)` return type. Adding a fifth
strategy is one file + one registry line.

## Real evaluation numbers

Produced by `python -m scripts.evaluate_models` on 820 MovieLens-100K users.
Per-user temporal last-5 holdout, min 20 train ratings, relevance = rating ≥ 4,
K = 10, models fit on TRAIN only.

| Strategy | Precision@10 | Recall@10 | NDCG@10 | Coverage | RMSE | MAE |
|----------|--------------|-----------|---------|----------|------|-----|
| Popularity | 0.02317 | 0.06762 | 0.04758 | 0.04221 | — | — |
| Content | 0.00622 | 0.01880 | 0.01376 | 0.25684 | — | — |
| **Collaborative** | **0.04793** | **0.15217** | **0.11612** | 0.12961 | **1.073** | **0.841** |
| Hybrid | 0.04146 | 0.12754 | 0.09487 | 0.15101 | — | — |

Interpretation and tuning suggestions in [docs/model_evaluation.md](docs/model_evaluation.md).

## Honest limitations

- **Hybrid does NOT beat pure CF** on Precision / Recall / NDCG at K=10 on
  this dataset with these weights. It wins on coverage and cold-start
  robustness — see the tuning section if you want to reverse the ranking
  outcome.
- **RMSE / MAE** are only meaningful for the collaborative model. Ranking-
  only recommenders honestly report `—` instead of faking a value.
- **Not deployed to any environment**. Docker files exist and are authored
  but have not been exercised (Docker isn't installed here).
- **No real authentication** — the demo trusts `user_id` from the client.
- **Frontend execution unverified here** — Node.js is not installed on the
  dev machine. The frontend is written against the API shape that the
  running Python server produced during integration testing.
- **Evaluation is single-run** — no confidence intervals; add bootstrapping
  before treating the numbers as statistically tight.
- **TMDB integration is optional and off by default** — poster/overview
  enrichment requires an API key.

## Screenshots

**None are included intentionally.** No frontend screenshots were captured
because Node.js / npm is not installed on the development machine (see
[PROJECT_STATUS.md](PROJECT_STATUS.md)). Rather than fabricate images or
stage mockups, this section documents the exact screens a reviewer should
see after running the app locally:

| Route | What you'll see |
|-------|-----------------|
| `/` | Cinematic hero driven by top-1 Bayesian-popularity movie, trending rail, personalized rail (only if user has signals), genre discovery rails |
| `/discover` | Search + genre chip filter + sort + 24-per-page grid of MovieCards |
| `/movies/:id` | Title, year, genres, mean rating, rating control 1..5, favorite toggle, honest "why this appears" reasons, TF-IDF similar titles |
| `/for-you` | 4-strategy chip row (Hybrid / Collaborative / Content / Popularity) + top-K slider + component-score breakdown per card |
| `/onboarding` | Genre picker + seed-movie search + save |
| `/favorites` | Persisted favorites with remove action |
| `/ratings` | Reverse-chronological list of saved ratings |
| `/insights` | Dataset summary + Recharts bar chart of Precision/Recall/NDCG/Coverage + full metrics table (real numbers from `artifacts/evaluation.json`) |
| `/about` | Plain-language method + honest limitations |

Capture them yourself with any browser tool once `npm run dev` is
running. Please do not paste images into a fork without attribution to
the MovieLens dataset / this project.

## Testing

Backend: 24 tests, all passing (~5s)

- `unit/test_recommenders.py` — 12 tests: Bayesian suppression, exclude
  lists, CF cold-start, hybrid determinism, weight renormalisation, etc.
- `integration/test_api.py` — 12 tests: health / ready, pagination, genre
  filter, 404, rating validation, persistence, favorites idempotency,
  preferences roundtrip, analytics 503 without evaluation artifacts.

Frontend: Vitest + RTL smoke suite (`src/test/app.test.tsx`) covering App
mount, MovieCard, RecommendationCard, RatingControl. Cannot be executed on
the current machine (no Node).

Run backend:

```powershell
cd PROJECT2\backend
.\.venv\Scripts\python.exe -m pytest -q
```

Run frontend (needs Node):

```powershell
cd PROJECT2\frontend
npm run test:run
```

## API surface

Base path `/api/v1`. Full reference:
[docs/api_reference.md](docs/api_reference.md). Highlights:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` `/ready` | Liveness + component readiness flags |
| GET | `/movies` `/movies/search` `/movies/{id}` `/genres` | Catalogue |
| GET | `/recommendations/popular` | Bayesian-popular list |
| GET | `/recommendations/similar/{movie_id}` | Content-based neighbours |
| GET | `/recommendations/users/{user_id}` | Personalised (strategy query) |
| POST | `/recommendations` | Same, with genre / year filters in body |
| GET | `/recommendations/explanations/{movie_id}` | Honest reasons only |
| POST | `/ratings` · GET `/users/{id}/ratings` | Persisted 1..5 |
| POST/DELETE/GET | `/users/{id}/favorites[/{movie_id}]` | Idempotent |
| PUT/GET | `/users/{id}/preferences` | Genres + seed_movie_ids |
| GET | `/analytics/overview` | Dataset + model version |
| GET | `/analytics/model-comparison` | Real metrics; 503 if not run |

Live Swagger at `/docs`.

## Documentation

- [Architecture](docs/architecture.md) — system + request-lifecycle Mermaid
  diagrams, module responsibility, failure modes, extension points
- [Data dictionary](docs/data_dictionary.md) — raw MovieLens files,
  processed CSVs, artifacts, SQLite tables, field mapping, PII notes
- [Model evaluation](docs/model_evaluation.md) — protocol, metrics, real
  numbers, honest interpretation, tuning suggestions
- [API reference](docs/api_reference.md) — endpoints, envelopes, examples
- [Deployment](docs/deployment.md) — local, Docker, config matrix,
  migrations, cloud topology, checklist, what's not ready
- [Demo script](docs/demo_script.md) — 10-minute walkthrough with talking
  points and things NOT to say
- [PROJECT_STATUS.md](PROJECT_STATUS.md) — live status log, verified numbers

## Repo layout

```
PROJECT2/
  backend/
    app/
      api/routes/all_routes.py
      core/{config,logging,exceptions}.py
      db/base.py
      integrations/tmdb.py
      models/db_models.py
      recommender/{base,popularity,content_based,collaborative,hybrid,explanations,registry}.py
      repositories/repository.py
      schemas/schemas.py
      services/domain.py
      main.py
    scripts/{download_dataset,preprocess_data,train_models,evaluate_models}.py
    tests/{conftest.py, unit/test_recommenders.py, integration/test_api.py}
    data/            (git-ignored) raw + processed
    artifacts/       (git-ignored) joblib + JSON
    requirements.txt, pytest.ini, .env.example
  frontend/
    src/
      api/{client.ts,queries.ts}
      components/{Layout,movie,ui,RatingControl}.tsx
      hooks/useUser.ts
      pages/{Home,Discover,MovieDetails,Personalized,Onboarding,Favorites,MyRatings,ModelInsights,About}.tsx
      test/{setup.ts,mockFetch.ts,app.test.tsx}
      types/api.ts
      App.tsx, main.tsx, index.css, vite-env.d.ts
    package.json, tsconfig.json, vite.config.ts, tailwind.config.js, postcss.config.js, index.html, .env.example
  docs/
    architecture.md, data_dictionary.md, model_evaluation.md,
    api_reference.md, deployment.md, demo_script.md
  Dockerfile
  docker-compose.yml
  PROJECT_STATUS.md
  README.md
  .gitignore
```

## License / attribution

Uses the public **MovieLens 100K** dataset from GroupLens Research
(<https://grouplens.org/datasets/movielens/>). Movie titles and genres are
factual data. TMDB integration targets the
[TMDB v3 API](https://www.themoviedb.org/documentation/api) and its
attribution requirements if enabled.
