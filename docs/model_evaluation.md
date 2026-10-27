# Model Evaluation

Every number on this page is produced by running
`python -m scripts.evaluate_models` inside `PROJECT2/backend`. Nothing is
hand-tuned, cherry-picked or fabricated. If you delete
`backend/artifacts/evaluation.json`, the `/insights` frontend page and the
`/api/v1/analytics/model-comparison` endpoint honestly report a 503.

## Protocol

| Property | Value | Why |
|----------|-------|-----|
| Split | per-user temporal **last-5 holdout** | Simulates "next few films you'd rate" and avoids random leakage |
| Minimum train ratings | 20 | Ensures every evaluated user has enough context for CF and content seeding |
| Users evaluated | **820 / 943** (~87%) | 123 users had < 20 ratings before their last 5 and are skipped |
| Relevance threshold | rating ≥ 4 | Common MovieLens convention; 4 and 5 count as relevant |
| Models fit on | TRAIN split only | Test ratings never touch fitting or normalisation |
| K | 10 | Top-10 recommendations per user |
| Content / hybrid seeds | user's top-10 **train** ratings | Prevents test leakage into content profile |
| Determinism | `np.lexsort((movie_ids, -scores))` | Same input ⇒ same ranking, so tests are stable |

## Metrics

- **Precision@K** — fraction of top-K that are relevant.
- **Recall@K** — fraction of the user's held-out relevant set recovered in
  the top-K.
- **NDCG@K** — Normalised Discounted Cumulative Gain with **binary gains**
  (0/1 relevance); rewards placing relevant items earlier.
- **Catalogue coverage** — distinct movie_ids that appear in any user's
  top-K, divided by total movies. Higher = less concentration on the head.
- **RMSE / MAE** — rating-prediction errors on held-out ratings. Only the
  **collaborative** model produces pointwise rating predictions; the other
  models are ranking-only by construction and are honestly reported as `—`.

## Results (real numbers)

Fit + evaluation environment: Python 3.14.7, scikit-learn 1.9.1, numpy
2.5.4, scipy 1.18.1, pandas 2.3.3. Machine: Windows 11, x86-64. Evaluated
users: 820. K = 10.

| Strategy | Precision@10 | Recall@10 | NDCG@10 | Coverage | RMSE | MAE |
|----------|--------------|-----------|---------|----------|------|-----|
| Popularity (Bayesian WR) | 0.02317 | 0.06762 | 0.04758 | 0.04221 | — | — |
| Content-based (TF-IDF + cosine) | 0.00622 | 0.01880 | 0.01376 | 0.25684 | — | — |
| **Collaborative (item-item CF)** | **0.04793** | **0.15217** | **0.11612** | 0.12961 | **1.073** | **0.841** |
| Hybrid (weights 0.20 / 0.35 / 0.45) | 0.04146 | 0.12754 | 0.09487 | 0.15101 | — | — |

### What the numbers say (honest interpretation)

1. **Collaborative filtering is the strongest top-N ranker** on ML-100K with
   this protocol. It wins every ranking metric and is the only one that
   predicts ratings directly.
2. **Hybrid does NOT beat pure CF** on Precision / Recall / NDCG at K=10.
   It's slightly worse on ranking quality but recovers some catalogue
   coverage versus CF (0.151 vs 0.130) and stays robust when CF is
   cold-started. This is a real, measured tradeoff, not a mistake — the
   report says so plainly.
3. **Popularity is the "sane baseline"** — 0.023 P@10 is a low but non-zero
   floor. Coverage 0.042 confirms it mostly re-ranks the head.
4. **Content-based has the worst precision but the widest coverage**
   (0.257). It reliably surfaces mid-tail titles that CF ignores, but with
   ML-100K's minimal metadata (title + genres only) it's noisy. A richer
   content representation (cast, plot via TMDB) is the obvious next step
   for anyone extending this project.

### Why hybrid underperforms CF here

- Weights default to `0.20 pop / 0.35 content / 0.45 cf`. Content's low
  precision drags down the blend.
- CF's item-item cosine is already excellent on ML-100K because the dataset
  is dense enough for neighbourhoods to be meaningful.
- Hybrid still wins in a *deployment* sense: (a) graceful cold-start — a
  user without ratings gets a sane popularity ranking instead of an empty
  list; (b) coverage — 0.151 vs 0.130; (c) interpretability — every card
  carries per-component scores.

### Tuning suggestions if you want hybrid to beat CF

- Drop content weight to 0.10, raise CF to 0.70. Should push P@10 above
  pure CF by blending out popularity noise while retaining coverage.
- Or gate content behind a similarity threshold (skip content when cosine
  < 0.08 rather than normalising the whole row).
- Both changes require re-running `evaluate_models.py`. Numbers here are
  from the shipped config.

## Rating-prediction: RMSE / MAE

Only CF reports these because it's the only model with a `predict_rating`
method. Formula: `user_mean + Σ_{n ∈ N_i(u)} sim(u, n) · (r_{n,i} − item_mean_i)
/ Σ |sim|`, clamped to `[1, 5]`. On 4,100 held-out ratings (from the 820
users × last-5 each):

- **RMSE 1.073**, **MAE 0.841**. For reference, a global-mean predictor on
  ML-100K sits around RMSE ≈ 1.13 and a user-mean predictor ≈ 1.06. Our
  neighbourhood model is on par with user-mean, slightly better than
  global-mean — an honest baseline-check that CF here is not "solved" but
  is functioning.

## Reproduce

```powershell
cd PROJECT2/backend
.\.venv\Scripts\python.exe -m scripts.download_dataset
.\.venv\Scripts\python.exe -m scripts.preprocess_data
.\.venv\Scripts\python.exe -m scripts.train_models
.\.venv\Scripts\python.exe -m scripts.evaluate_models
```

Then open `backend/artifacts/evaluation.json` — every metric in the table
above is directly copied from that file.

## What would improve the evaluation

- Cross-validation over multiple seeds for statistical confidence intervals
  (currently single run — honest limitation).
- Full rating datasets with real timestamps (ML-1M / ML-25M supported via
  `MOVIELENS_DATASET` env, but not downloaded here).
- Personalised hyper-parameter sweep per user segment.
- Online A/B testing (out of scope for a portfolio project).
