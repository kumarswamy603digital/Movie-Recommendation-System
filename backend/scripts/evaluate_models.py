"""Evaluate all four strategies on a reproducible per-user train/test split.

Protocol:
- For each user with >= 20 ratings, hold out their 5 most recent interactions
  as test items. All other interactions form the training set.
- Fit recommenders on train only (no data leakage into test).
- Score each strategy by ranking every item the user hasn't rated in TRAIN,
  and count how many held-out TEST items appear in the top-K.
- "Relevant" for a user = a test item with rating >= 4.
- Report Precision@K, Recall@K, NDCG@K (binary relevance), Catalog Coverage.
- Additionally evaluate rating prediction on held-out ratings (collaborative
  supports this) via RMSE / MAE.

Outputs (JSON): artifacts/evaluation.json
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings  # noqa: E402
from app.recommender.collaborative import CollaborativeRecommender  # noqa: E402
from app.recommender.content_based import ContentBasedRecommender  # noqa: E402
from app.recommender.hybrid import HybridRecommender, HybridWeights  # noqa: E402
from app.recommender.popularity import PopularityRecommender  # noqa: E402


TOP_K = 10
MIN_TRAIN_PER_USER = 20
HOLDOUT_PER_USER = 5
REL_THRESHOLD = 4  # ratings >= this count as "relevant"


def _split(ratings: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-user last-N split. Uses the timestamp column if present, else order."""
    if "timestamp" in ratings.columns:
        ratings = ratings.sort_values(["user_id", "timestamp"], kind="stable")
    else:
        ratings = ratings.reset_index(drop=True)
    test_rows: list[int] = []
    for uid, grp in ratings.groupby("user_id", sort=True):
        if len(grp) < MIN_TRAIN_PER_USER:
            continue
        for idx in grp.index[-HOLDOUT_PER_USER:]:
            test_rows.append(idx)
    mask = ratings.index.isin(test_rows)
    return ratings[~mask].copy(), ratings[mask].copy()


def _precision_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    top = ranked[:k]
    hits = sum(1 for m in top if m in relevant)
    return hits / float(k)


def _recall_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    hits = sum(1 for m in ranked[:k] if m in relevant)
    return hits / float(len(relevant))


def _ndcg_at_k(ranked: list[int], relevant: set[int], k: int) -> float:
    if not relevant:
        return 0.0
    dcg = sum(1.0 / math.log2(i + 2) for i, m in enumerate(ranked[:k]) if m in relevant)
    ideal_n = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_n))
    return dcg / idcg if idcg > 0 else 0.0


def _coverage(all_ranked: set[int], catalogue_size: int) -> float:
    if catalogue_size <= 0:
        return 0.0
    return len(all_ranked) / float(catalogue_size)


def _rmse_mae(preds: list[float], actuals: list[float]) -> tuple[float | None, float | None]:
    if not preds:
        return None, None
    arr_p = np.array(preds, dtype=float)
    arr_a = np.array(actuals, dtype=float)
    err = arr_p - arr_a
    return float(np.sqrt(np.mean(err ** 2))), float(np.mean(np.abs(err)))


def main() -> int:
    processed = Path(settings.processed_dir)
    if not (processed / "movies.csv").exists():
        print("Run scripts.preprocess_data first.", file=sys.stderr)
        return 2
    # We need timestamps for the temporal split; use raw ml-100k if not in CSV.
    ratings_raw = pd.read_csv(processed / "ratings.csv")
    movies = pd.read_csv(processed / "movies.csv")

    # Attach timestamps from raw dataset for deterministic last-N selection.
    if "timestamp" not in ratings_raw.columns and settings.movielens_dataset == "ml-100k":
        raw = pd.read_csv(
            Path(settings.data_dir) / "ml-100k" / "u.data",
            sep="\t", header=None, names=["user_id", "movie_id", "rating", "timestamp"],
            encoding="latin-1",
        )
        ratings_raw = ratings_raw.merge(
            raw[["user_id", "movie_id", "timestamp"]], on=["user_id", "movie_id"], how="left",
        )

    train, test = _split(ratings_raw)
    print(f"Split: train={len(train):,} test={len(test):,} "
          f"(evaluating only users with >= {MIN_TRAIN_PER_USER} ratings).")

    # Fit on train ONLY.
    pop = PopularityRecommender.fit(train, min_ratings=settings.popularity_min_ratings)
    con = ContentBasedRecommender.fit(movies)
    cf = CollaborativeRecommender.fit(train)
    hy = HybridRecommender(
        pop, con, cf,
        weights=HybridWeights(
            settings.hybrid_weight_popularity,
            settings.hybrid_weight_content,
            settings.hybrid_weight_collaborative,
        ),
    )

    eval_users = sorted({int(u) for u in test["user_id"].unique()})
    print(f"Users eligible for evaluation: {len(eval_users):,}")

    stats = {k: {"p": [], "r": [], "n": [], "seen": set()} for k in ["popularity", "content", "collaborative", "hybrid"]}
    preds: list[float] = []
    actuals: list[float] = []

    for u in eval_users:
        user_train = train[train["user_id"] == u].set_index("movie_id")["rating"]
        user_test = test[test["user_id"] == u]
        relevant = {int(m) for m, r in zip(user_test["movie_id"], user_test["rating"]) if float(r) >= REL_THRESHOLD}
        exclude = set(int(m) for m in user_train.index)
        if not relevant:
            continue

        pop_list = [s.movie_id for s in pop.global_top(top_k=TOP_K, exclude_movie_ids=exclude)]
        stats["popularity"]["p"].append(_precision_at_k(pop_list, relevant, TOP_K))
        stats["popularity"]["r"].append(_recall_at_k(pop_list, relevant, TOP_K))
        stats["popularity"]["n"].append(_ndcg_at_k(pop_list, relevant, TOP_K))
        stats["popularity"]["seen"].update(pop_list)

        # Content: similarity to user's top-rated training items.
        if not user_train.empty:
            seeds = [int(m) for m, r in user_train.sort_values(ascending=False).head(10).items()]
            agg: dict[int, float] = {}
            for s in seeds:
                for sc in con.similar_to_movie(s, exclude_movie_ids=exclude, top_k=TOP_K * 2):
                    agg[sc.movie_id] = agg.get(sc.movie_id, 0.0) + sc.score
            con_list = [m for m, _ in sorted(agg.items(), key=lambda x: (-x[1], x[0]))[:TOP_K]]
        else:
            con_list = []
        stats["content"]["p"].append(_precision_at_k(con_list, relevant, TOP_K))
        stats["content"]["r"].append(_recall_at_k(con_list, relevant, TOP_K))
        stats["content"]["n"].append(_ndcg_at_k(con_list, relevant, TOP_K))
        stats["content"]["seen"].update(con_list)

        cf_list = [s.movie_id for s in cf.top_for_user(u, user_train, exclude, TOP_K)]
        stats["collaborative"]["p"].append(_precision_at_k(cf_list, relevant, TOP_K))
        stats["collaborative"]["r"].append(_recall_at_k(cf_list, relevant, TOP_K))
        stats["collaborative"]["n"].append(_ndcg_at_k(cf_list, relevant, TOP_K))
        stats["collaborative"]["seen"].update(cf_list)

        hy_list = [s.movie_id for s in hy.rank(
            user_id=u, ratings_by_user=user_train, exclude_movie_ids=exclude,
            top_k=TOP_K, seed_movie_ids=[int(m) for m, r in user_train.sort_values(ascending=False).head(10).items()],
        )]
        stats["hybrid"]["p"].append(_precision_at_k(hy_list, relevant, TOP_K))
        stats["hybrid"]["r"].append(_recall_at_k(hy_list, relevant, TOP_K))
        stats["hybrid"]["n"].append(_ndcg_at_k(hy_list, relevant, TOP_K))
        stats["hybrid"]["seen"].update(hy_list)

        # Rating-prediction error (only for CF).
        for mid, val in zip(user_test["movie_id"].astype(int), user_test["rating"].astype(float)):
            p = cf.predict_rating(u, int(mid))
            if p is not None:
                preds.append(p)
                actuals.append(float(val))

    catalogue_size = int(len(movies))
    metrics: list[dict] = []
    for strat, s in stats.items():
        n = len(s["p"]) or 1
        metrics.append({
            "model": strat,
            "evaluation_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "top_k": TOP_K,
            "precision_at_k": round(float(np.mean(s["p"])) if s["p"] else 0.0, 5),
            "recall_at_k": round(float(np.mean(s["r"])) if s["r"] else 0.0, 5),
            "ndcg_at_k": round(float(np.mean(s["n"])) if s["n"] else 0.0, 5),
            "coverage": round(_coverage(s["seen"], catalogue_size), 5),
            "rmse": None,
            "mae": None,
            "notes": f"evaluated on {len(s['p']):,} users with held-out last-{HOLDOUT_PER_USER} interactions.",
        })
    rmse, mae = _rmse_mae(preds, actuals)
    for row in metrics:
        if row["model"] == "collaborative":
            row["rmse"] = round(rmse, 5) if rmse is not None else None
            row["mae"] = round(mae, 5) if mae is not None else None

    payload = {
        "protocol": (
            f"Per-user temporal last-{HOLDOUT_PER_USER} holdout, min {MIN_TRAIN_PER_USER} "
            f"train ratings per user; relevant = rating >= {REL_THRESHOLD}; "
            f"metrics averaged across users. Models fit only on TRAIN."
        ),
        "top_k": TOP_K,
        "n_eval_users": len(eval_users),
        "n_relevant_users": int(len(stats["popularity"]["p"])),
        "dataset_version": settings.movielens_dataset,
        "hybrid_weights": {
            "popularity": settings.hybrid_weight_popularity,
            "content": settings.hybrid_weight_content,
            "collaborative": settings.hybrid_weight_collaborative,
        },
        "metrics": metrics,
        "rating_prediction": {
            "n_predictions": len(preds),
            "rmse": round(rmse, 5) if rmse is not None else None,
            "mae": round(mae, 5) if mae is not None else None,
            "model": "collaborative",
        },
    }

    arts = Path(settings.artifacts_dir)
    arts.mkdir(parents=True, exist_ok=True)
    (arts / "evaluation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
