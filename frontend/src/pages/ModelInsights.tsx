// ModelInsights — real, offline evaluation numbers rendered from the API.
// Includes a bar chart via recharts and an honest note on the hybrid.

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useModelComparison, useOverview } from "../api/queries";
import { ErrorState, LoadingSkeleton, EmptyState } from "../components/ui";
import type { ModelMetrics } from "../types/api";

const METRIC_KEYS: {
  key: keyof ModelMetrics;
  label: string;
  higherIsBetter: boolean;
}[] = [
  { key: "precision_at_k", label: "Precision@K", higherIsBetter: true },
  { key: "recall_at_k", label: "Recall@K", higherIsBetter: true },
  { key: "ndcg_at_k", label: "NDCG@K", higherIsBetter: true },
  { key: "coverage", label: "Coverage", higherIsBetter: true },
  { key: "rmse", label: "RMSE", higherIsBetter: false },
  { key: "mae", label: "MAE", higherIsBetter: false },
];

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(4);
  return String(v);
}

export default function ModelInsights() {
  const cmp = useModelComparison();
  const ovw = useOverview();

  const metrics = cmp.data?.metrics ?? [];
  const chartData = metrics.map((m) => ({
    model: m.model,
    "Precision@K": m.precision_at_k ?? 0,
    "Recall@K": m.recall_at_k ?? 0,
    "NDCG@K": m.ndcg_at_k ?? 0,
    Coverage: m.coverage ?? 0,
  }));

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">Model insights</h1>
        <p className="muted text-sm">
          Offline evaluation from <code>scripts/evaluate_models.py</code>. Numbers
          are computed on real MovieLens holdouts — not curated or hand-tuned.
        </p>
      </header>

      {ovw.data ? (
        <div className="card grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <Stat label="Dataset" value={ovw.data.dataset?.dataset_version ?? "—"} />
          <Stat label="Users" value={ovw.data.dataset?.n_users ?? "—"} />
          <Stat label="Movies" value={ovw.data.n_catalog_movies ?? ovw.data.dataset?.n_movies ?? "—"} />
          <Stat label="Ratings" value={ovw.data.dataset?.n_ratings ?? "—"} />
          <Stat label="Model version" value={ovw.data.model_version ?? "—"} />
          <Stat label="CF fitted users" value={ovw.data.n_fitted_users ?? "—"} />
        </div>
      ) : null}

      {cmp.isLoading || ovw.isLoading ? <LoadingSkeleton rows={3} /> : null}
      {cmp.error ? (
        <ErrorState
          title="Evaluation not available"
          message={(cmp.error as Error).message}
          onRetry={() => cmp.refetch()}
        />
      ) : null}
      {cmp.data && cmp.data.metrics.length === 0 ? (
        <EmptyState
          title="No metrics stored"
          message="Run scripts/evaluate_models.py to write artifacts/evaluation.json."
        />
      ) : null}

      {metrics.length > 0 ? (
        <>
          <div className="card">
            <div className="mb-3 text-sm font-semibold">
              Ranking quality · K = {cmp.data?.top_k ?? 10} · protocol:{" "}
              <span className="muted">{cmp.data?.protocol ?? "—"}</span>
            </div>
            <div className="h-72 w-full">
              <ResponsiveContainer>
                <BarChart data={chartData}>
                  <CartesianGrid stroke="#1e2938" strokeDasharray="3 3" />
                  <XAxis dataKey="model" stroke="#94a3b8" />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip contentStyle={{ background: "#12161c", border: "1px solid #1e293b" }} />
                  <Legend />
                  <Bar dataKey="Precision@K" fill="#e50914" />
                  <Bar dataKey="Recall@K" fill="#f97316" />
                  <Bar dataKey="NDCG@K" fill="#22c55e" />
                  <Bar dataKey="Coverage" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left muted">
                  <th className="py-2">Model</th>
                  {METRIC_KEYS.map((m) => (
                    <th key={m.key as string} className="py-2 text-right">
                      {m.label}
                    </th>
                  ))}
                  <th className="py-2">Notes</th>
                </tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={m.model} className="border-t border-slate-800">
                    <td className="py-2 font-semibold">{m.model}</td>
                    {METRIC_KEYS.map((mk) => (
                      <td key={mk.key as string} className="py-2 text-right tabular-nums">
                        {fmt(m[mk.key])}
                      </td>
                    ))}
                    <td className="py-2 text-xs muted">{m.notes ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted mt-3 text-xs">
              Interpretation: on MovieLens 100K with these settings, the pure
              item-item CF model edges out the hybrid on top-N metrics. The
              hybrid trades a small precision hit for higher catalogue coverage.
              RMSE / MAE are rating-prediction metrics computed on CF only; the
              other models are ranking-only by construction.
            </p>
          </div>
        </>
      ) : null}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="muted text-xs uppercase tracking-wide">{label}</div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
