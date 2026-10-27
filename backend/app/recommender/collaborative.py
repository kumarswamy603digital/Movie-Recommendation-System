"""Collaborative filtering: item-item cosine on the sparse user x item rating
matrix, plus a mean-rating-biased baseline for score prediction.

Also exposes a helper to compute predicted ratings so evaluation scripts can
report RMSE/MAE. SVD is intentionally not baked in as the primary path —
item-item cosine is transparent, deterministic, and works well for
MovieLens-sized data. A TruncatedSVD variant is provided as an optional
secondary scorer for the hybrid blend.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

from app.recommender.base import Recommender, Scored, coerce_movie_ids


@dataclass
class CFState:
    user_ids: np.ndarray            # (U,)
    movie_ids: np.ndarray           # (M,)
    user_index: dict[int, int]
    movie_index: dict[int, int]
    R: sparse.csr_matrix            # (U x M) ratings (0 = unrated)
    item_sim: sparse.csr_matrix     # (M x M) cosine similarities (sparse)
    global_mean: float
    item_mean: np.ndarray           # (M,) mean over users who rated the item
    item_pop: np.ndarray            # (M,) count of ratings per item
    svd: TruncatedSVD | None
    U: np.ndarray | None            # user factors (from SVD on centered R)


class CollaborativeRecommender(Recommender):
    name = "collaborative"

    def __init__(self, state: CFState | None = None) -> None:
        self._st = state

    # -------- lifecycle --------

    @classmethod
    def fit(
        cls,
        ratings: pd.DataFrame,
        svd_components: int = 32,
        sim_neighbors: int = 200,
        seed: int = 42,
    ) -> "CollaborativeRecommender":
        """`ratings` needs columns user_id, movie_id, rating (float 1..5)."""
        if ratings.empty:
            return cls()

        user_ids = np.sort(ratings["user_id"].unique().astype(np.int64))
        movie_ids = np.sort(ratings["movie_id"].unique().astype(np.int64))
        u_idx = {int(u): i for i, u in enumerate(user_ids)}
        m_idx = {int(m): i for i, m in enumerate(movie_ids)}

        rows = ratings["user_id"].map(u_idx).to_numpy(dtype=np.int64)
        cols = ratings["movie_id"].map(m_idx).to_numpy(dtype=np.int64)
        vals = ratings["rating"].to_numpy(dtype=np.float64)
        R = sparse.csr_matrix((vals, (rows, cols)), shape=(len(user_ids), len(movie_ids)))

        # Item vectors: transpose, so cols become items.
        Rt = R.T.tocsr()  # (M x U)
        # Cosine similarity via sklearn. Sparse-out on values < tiny threshold
        # to keep memory low.
        sim_dense = cosine_similarity(Rt, dense_output=False)
        # Keep only top-`sim_neighbors` per row (sparsify).
        n_items = sim_dense.shape[0]
        sim_csr = sparse.lil_matrix((n_items, n_items), dtype=np.float32)
        k = min(sim_neighbors, n_items)
        for i in range(n_items):
            row = np.asarray(sim_dense[i].todense()).ravel() if sparse.issparse(sim_dense[i]) else sim_dense[i]
            # Exclude self.
            row[i] = 0.0
            top = np.argpartition(-row, kth=k - 1)[:k]
            sim_csr[i, top] = row[top]
        item_sim = sim_csr.tocsr()

        global_mean = float(vals.mean())
        item_sum = np.asarray(R.sum(axis=0)).ravel()
        item_pop = np.asarray((R != 0).sum(axis=0)).ravel()
        with np.errstate(divide="ignore", invalid="ignore"):
            item_mean = np.where(item_pop > 0, item_sum / np.maximum(item_pop, 1), global_mean)

        svd = None
        U = None
        if svd_components > 0 and R.shape[0] > 1 and R.shape[1] > 1:
            try:
                # Center each user's ratings so SVD learns preferences not item bias.
                dense_R = R.toarray()
                means = np.array([
                    dense_R[i, dense_R[i] > 0].mean() if (dense_R[i] > 0).any() else global_mean
                    for i in range(dense_R.shape[0])
                ])
                centered = dense_R.copy()
                for i in range(centered.shape[0]):
                    mask = centered[i] > 0
                    centered[i, mask] = centered[i, mask] - means[i]
                svd = TruncatedSVD(
                    n_components=min(svd_components, min(R.shape) - 1),
                    random_state=seed,
                ).fit(centered)
                U = svd.transform(centered)
            except Exception:
                svd = None
                U = None

        state = CFState(
            user_ids=user_ids, movie_ids=movie_ids,
            user_index=u_idx, movie_index=m_idx,
            R=R, item_sim=item_sim,
            global_mean=global_mean, item_mean=item_mean, item_pop=item_pop,
            svd=svd, U=U,
        )
        return cls(state)

    def save(self, path: str) -> None:
        import joblib
        joblib.dump(self._st, path)

    @classmethod
    def load(cls, path: str) -> "CollaborativeRecommender":
        import joblib
        return CollaborativeRecommender(state=joblib.load(path))

    def is_ready(self) -> bool:
        return self._st is not None and self._st.R.shape[0] > 0

    # -------- queries --------

    def user_has_history(self, user_id: int) -> bool:
        if not self.is_ready():
            return False
        return int(user_id) in self._st.user_index

    def top_for_user(
        self,
        user_id: int,
        ratings_by_user: pd.Series | None,
        exclude_movie_ids: set[int],
        top_k: int,
    ) -> list[Scored]:
        """Score every unseen item via weighted sum of user's ratings over
        similar items. Cold-start (user not in training set) returns []."""
        if not self.is_ready():
            return []
        st = self._st
        u = st.user_index.get(int(user_id))
        if u is None:
            return []
        # Aggregate the user's rating vector (index by item) via R row.
        rated = st.R[u].tocsr()
        # Score = R_row @ item_sim  (M,)
        scores = np.asarray((rated @ st.item_sim).todense()).ravel()
        # Exclude already-rated items.
        rated_cols = rated.indices
        scores[rated_cols] = -np.inf
        for mid in coerce_movie_ids(exclude_movie_ids):
            m = st.movie_index.get(mid)
            if m is not None:
                scores[m] = -np.inf
        order = np.argsort(-scores, kind="stable")[:top_k]
        out: list[Scored] = []
        for m in order:
            s = float(scores[m])
            if not np.isfinite(s) or s <= 0.0:
                continue
            out.append(Scored(movie_id=int(st.movie_ids[m]), score=s, components={"collaborative": s}))
        return out

    def predict_rating(self, user_id: int, movie_id: int) -> float | None:
        """Mean-biased baseline + item-neighbourhood residual. Clamped to [1,5]."""
        if not self.is_ready():
            return None
        st = self._st
        u = st.user_index.get(int(user_id))
        m = st.movie_index.get(int(movie_id))
        if u is None or m is None:
            return None
        # User mean over items they rated.
        row = st.R[u].toarray().ravel()
        rated_mask = row > 0
        if not rated_mask.any():
            return float(st.item_mean[m])
        user_mean = float(row[rated_mask].mean())
        # Weighted neighbourhood residual:
        neighbors = st.item_sim[m]
        if neighbors.nnz == 0:
            return float(np.clip(user_mean, 1, 5))
        cols = neighbors.indices
        w = neighbors.data
        common_mask = rated_mask[cols]
        if not common_mask.any():
            return float(np.clip(user_mean, 1, 5))
        resid = (row[cols][common_mask] - user_mean) * w[common_mask]
        denom = float(np.abs(w[common_mask]).sum())
        bias = float(resid.sum() / denom) if denom > 0 else 0.0
        return float(np.clip(user_mean + bias, 1.0, 5.0))

    def fitted_user_count(self) -> int:
        return int(self._st.user_ids.size) if self._st else 0
