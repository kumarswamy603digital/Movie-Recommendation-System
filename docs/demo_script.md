# Demo Script

A 10-minute walkthrough you can run in front of a reviewer or record for a
portfolio video. Assumes both servers are up:

```powershell
# Terminal 1 — backend
cd PROJECT2/backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# Terminal 2 — frontend (requires Node 20)
cd PROJECT2/frontend
npm run dev
```

Open **http://localhost:5173**.

---

## 0:00 — Home (1 min)

**Beat:** "Four different recommenders, one honest evaluation."

Point at the hero copy. Scroll down to the *Trending in the catalogue*
strip — this is the **Bayesian weighted rating** popularity table, not raw
count-of-ratings. Note the "user 1" chip in the header (demo identity).

## 1:00 — Discover (1 min)

**Beat:** "The catalogue is real, filterable data."

Type `alien` into search. Show results include *Alien*, *Aliens*, *Ghostbust*
etc. Click the *Sci-Fi* genre chip — results narrow. Switch Sort to
*Rating* and then *Year* — paging resets to 1 automatically.

## 2:00 — Movie details (1 min)

**Beat:** "Explanations come with signals, not vibes."

Open **Aliens (1986)**. Highlight:
- The `mean_rating` and `rating_count` header (from the real dataset).
- The *Your rating* control — click **5** — a green confirmation appears.
- The **Why this appears** panel shows a *content* reason with the concrete
  seed titles that produced it.
- The **Similar titles** grid — TF-IDF cosine neighbours.

## 3:00 — Cold-start reset (1 min)

**Beat:** "Cold start falls back honestly."

Change the demo user id in the header to something like `500` (a low-rating
user). Navigate to *For You* — the response's `personalized` field is false
and the `notes` array says exactly why. Nothing was invented.

## 4:00 — Onboarding (1 min)

**Beat:** "Cold users can seed their own profile."

Go to *Onboarding*, pick 3 genres, add 3 seed movies via the search field,
Save & view picks. Auto-redirects to *For You* — content-based now returns
real reasons and the hybrid card shows per-component scores
(`popularity:0.42 · content:0.62 · cf:0.05`).

## 5:00 — Personalized page (1 min)

**Beat:** "Same interface, four strategies."

Click the chip row: **Hybrid → Collaborative → Content → Popularity**.
Same user id, same top-K, four different rankings. Point out the
`score` + `component_scores` breakdown under each card.

## 6:00 — Favorites + Ratings (1 min)

**Beat:** "Real persistence in SQLite."

Add two favorites from the recommendation grid (`☆ Add to favorites`). Then
open *Favorites* — the two titles are there. Refresh, still there. Open
*My Ratings* — the earlier 5-star on *Aliens* is recorded with a date.

## 7:00 — Model Insights (2 min)

**Beat:** "Numbers are real and unflattering."

Open *Insights*. Walk the numbers table:
- **Collaborative is the strongest top-N ranker here** — P@10 = 0.048,
  NDCG@10 = 0.116.
- **Hybrid does not beat CF** — 0.041 P@10. Say it out loud. Explain the
  tradeoff (coverage 0.151 vs 0.130, graceful cold-start).
- **Content has terrible precision (0.006) but excellent coverage
  (0.257)** — this is a real characteristic of TF-IDF on minimal metadata.
- **RMSE 1.073 / MAE 0.841** — reported only for CF because it's the only
  model that predicts a rating.

Hover the recharts bar chart to show relative heights. Mention the protocol
row: "820 users, last-5 holdout, relevance ≥ 4, K=10, fit on TRAIN only."

## 9:00 — About + close (1 min)

**Beat:** "Honest limitations section is on purpose."

Open *About*. Scroll to *Honest limitations*. Say: "Hybrid underperforms
here, TMDB integration is optional, ML-100K timestamps are second-
precision. Everything measured is reported."

Close: `/docs` in a new tab to show OpenAPI / Swagger.

---

## Optional advanced demo

- **API only** — hit endpoints from PowerShell:
  ```powershell
  Invoke-RestMethod http://localhost:8000/api/v1/recommendations/users/42?strategy=hybrid |
    ConvertTo-Json -Depth 4
  ```
- **Backend tests** — `pytest -q` → 24 passed in ~5s.
- **Rerun pipeline** — delete `backend/artifacts/*` and run
  `python -m scripts.train_models && python -m scripts.evaluate_models` to
  show the whole flow regenerates identically (with the same lexsort-
  deterministic tie-breaking).

## What NOT to say during a demo

- Don't claim "production ready" — auth is a demo shim.
- Don't claim "deployed" — no cloud instance exists.
- Don't claim hybrid beats CF — it doesn't on this data.
- Don't invent posters or TMDB data if `TMDB_API_KEY` isn't set — the API
  honestly returns null.
