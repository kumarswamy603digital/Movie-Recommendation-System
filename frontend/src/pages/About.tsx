// About — plain-language description of what this project is, the four
// recommenders, the evaluation protocol, and an honest limitations section.

import { Link } from "react-router-dom";

export default function About() {
  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">About this project</h1>
        <p className="muted text-sm">
          A Movie Recommendation System built as an ML internship portfolio
          piece. Backend in FastAPI, front end in React + Vite, dataset:
          MovieLens 100K.
        </p>
      </header>

      <div className="card space-y-3 text-sm">
        <h2 className="text-lg font-semibold">The four recommenders</h2>
        <ul className="list-disc space-y-2 pl-5">
          <li>
            <b>Popularity</b> — Bayesian weighted rating (IMDb Top-250 formula).
            Suppresses titles with fewer than <code>POPULARITY_MIN_RATINGS</code>{" "}
            ratings so the tail can't hijack the top-K.
          </li>
          <li>
            <b>Content-based</b> — TF-IDF over genres + title tokens, cosine
            similarity against a seed profile built from the user's top-rated
            titles.
          </li>
          <li>
            <b>Collaborative filtering</b> — item-item scoring on the sparse
            user×item matrix (cosine, sparsified to top-200 neighbours/row),
            plus TruncatedSVD on the user-centred matrix and mean-biased
            neighbourhood rating prediction for RMSE/MAE.
          </li>
          <li>
            <b>Hybrid</b> — independent min-max normalisation of each component
            score, weighted blend (renormalised over present components), and
            deterministic tie-breaking by movie id via <code>np.lexsort</code>.
          </li>
        </ul>
      </div>

      <div className="card space-y-2 text-sm">
        <h2 className="text-lg font-semibold">Offline evaluation</h2>
        <p>
          Per-user <b>temporal last-5 holdout</b>. A user must have at least 20
          ratings to be evaluated. <b>Relevant = rating ≥ 4</b>. We fit on the
          train split only. Reported metrics: Precision@10, Recall@10, NDCG@10
          (binary gains), catalogue coverage, and RMSE/MAE for the CF rating
          predictor.
        </p>
        <p>
          Numbers shown on <Link to="/insights" className="text-accent underline">Insights</Link>{" "}
          come from <code>artifacts/evaluation.json</code> written by the
          evaluation script — nothing is hard-coded.
        </p>
      </div>

      <div className="card space-y-2 text-sm">
        <h2 className="text-lg font-semibold">Honest limitations</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Hybrid currently <b>does not</b> beat pure CF on Precision/Recall/NDCG
            at K=10 on ML-100K with the tuned weights. It trades precision for
            higher coverage and cold-start robustness.
          </li>
          <li>
            Ratings dataset has no explicit <em>timestamp</em> column in ML-100K
            — the file row order is a proxy for temporal ordering.
          </li>
          <li>
            Posters / overviews come from TMDB only when{" "}
            <code>TMDB_API_KEY</code> is configured; without a key, they are
            honestly reported as unavailable.
          </li>
          <li>
            Content-based signals are limited to title + genres in ML-100K. No
            plot / cast metadata unless TMDB is enabled.
          </li>
        </ul>
      </div>

      <div className="card text-sm">
        <h2 className="text-lg font-semibold">Explanations</h2>
        <p>
          Explanations are only emitted when the underlying signal is present:
          content similarity above 0.05, a positive CF component, or a
          meaningful popularity component. Otherwise the card honestly says{" "}
          <em>"popular in the catalogue"</em> and nothing more.
        </p>
      </div>
    </section>
  );
}
