# Deployment

Honest scope: this project has **not been deployed** to any public
environment. Everything below is what a productionisation pass would look
like — the code already handles most of it; a few steps are still manual.

## Local (verified on this machine)

See root [README](../README.md#quickstart). Summary:

```powershell
# Backend
cd PROJECT2/backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.download_dataset
.\.venv\Scripts\python.exe -m scripts.preprocess_data
.\.venv\Scripts\python.exe -m scripts.train_models
.\.venv\Scripts\python.exe -m scripts.evaluate_models
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Frontend (requires Node.js ≥ 20 — not installed on the current machine)
cd PROJECT2/frontend
npm install
npm run dev
```

## Docker

`Dockerfile` at project root builds the backend image.
`docker-compose.yml` wires backend + frontend services.

```powershell
docker compose up --build
# backend → http://localhost:8000/api/v1/health
# frontend → http://localhost:5173
```

Notes:
- Backend image installs from `PROJECT2/backend/requirements.txt` and runs
  uvicorn on `0.0.0.0:8000`.
- Frontend image is multi-stage: `node:20-alpine` builds with `npm run
  build`, then `nginx:alpine` serves the static `dist/` folder.
- Dataset download is baked into the backend image build to avoid a cold-
  start dependency on the Grouplens mirror. Delete the `RUN python -m
  scripts.download_dataset` line if you prefer to mount a volume.
- Volumes `artifacts` and `appdata` persist joblib models + SQLite DB across
  restarts.

## Configuration matrix

| Variable | Default | Notes |
|----------|---------|-------|
| `DATABASE_URL` | `sqlite:///./app.db` | Swap to `postgresql://…` for prod |
| `MOVIELENS_DATASET` | `ml-100k` | `ml-1m` and `ml-25m` also supported by the pipeline |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated |
| `HYBRID_WEIGHT_POPULARITY` | `0.20` | Renormalised on registry load |
| `HYBRID_WEIGHT_CONTENT` | `0.35` | |
| `HYBRID_WEIGHT_CF` | `0.45` | |
| `POPULARITY_MIN_RATINGS` | `20` | Bayesian suppression threshold |
| `TMDB_API_KEY` | *(empty)* | When set, movie lookups enrich poster / overview |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose registry loading |

## Migrations

Currently the app uses `Base.metadata.create_all()` on startup. Alembic is
installed but not wired. Production steps:

```powershell
cd PROJECT2/backend
.\.venv\Scripts\alembic init migrations
# Edit migrations/env.py to point at settings.database_url and import Base.metadata
.\.venv\Scripts\alembic revision --autogenerate -m "initial schema"
.\.venv\Scripts\alembic upgrade head
```

Then remove the `init_db()` call from `main.py`'s lifespan.

## Suggested cloud topology

```
  ┌──────────────┐        ┌────────────────────┐
  │ Static SPA   │  CDN   │  Object store      │
  │ (Vite build) ├────────┤  (posters / cache) │
  └──────┬───────┘        └────────────────────┘
         │ HTTPS
         ▼
  ┌──────────────────────────────┐
  │ Load balancer / API gateway  │
  └──────────┬───────────────────┘
             │ /api/v1
             ▼
  ┌───────────────────────┐   ┌───────────────────────┐
  │ FastAPI (container)   │──►│ Managed Postgres      │
  │  - uvicorn workers    │   └───────────────────────┘
  │  - registry warm      │
  └───────┬───────────────┘
          │ read joblib
          ▼
  ┌───────────────────────┐
  │ Blob mount or PVC     │
  │  *.joblib, CSV, JSON  │
  └───────────────────────┘
```

## Operational checklist

- [ ] Set `LOG_LEVEL=WARNING` and pipe stdout to your log aggregator.
- [ ] Add `prometheus-fastapi-instrumentator` for RED metrics.
- [ ] Move artifacts to S3 / GCS and load them lazily on first request.
- [ ] Rotate `TMDB_API_KEY` via your secret store, not env.
- [ ] Rate limit `/recommendations/*` — hybrid ranking is O(N candidates).
- [ ] Re-run pipeline on schedule (weekly for ML-100K; daily for a live
      dataset) — `train_models.py` and `evaluate_models.py` are idempotent.
- [ ] Backup SQLite / Postgres nightly.

## What is *not* ready for real production

- **Authentication** — demo mode; no accounts, no session tokens. Any
  `user_id` in the dataset range can read/write another user's ratings.
- **Personal data** — none captured (see [Data dictionary](data_dictionary.md))
  so GDPR / CCPA are trivially satisfied for the demo; a real deployment
  with signups needs a policy.
- **Horizontally scaled recommender warmup** — the registry fits per
  process; with N workers you pay the fit cost N times. Move to a
  shared cache (Redis) or a dedicated scoring service.

## Rollback

Artifacts carry a version string in `model_version.json`. If a fresh
training run regresses (see [Model evaluation](model_evaluation.md)):

```powershell
# Save the current artifacts, restore the previous ones
mv backend/artifacts backend/artifacts.$(Get-Date -Format yyyyMMdd-HHmm)
mv backend/artifacts.previous backend/artifacts
# uvicorn hot-swaps on next /ready check
```

For a real deployment with an object store, keep N last versions and flip
a pointer.
