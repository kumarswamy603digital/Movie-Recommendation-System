import { useState } from "react";
import { useUser } from "../hooks/useUser";
import { useForUser } from "../api/queries";
import { RecommendationGrid } from "../components/movie";
import { ErrorState, LoadingSkeleton, EmptyState } from "../components/ui";

type Strategy = "hybrid" | "popularity" | "content" | "collaborative";
const STRATS: { id: Strategy; label: string; hint: string }[] = [
  { id: "hybrid", label: "Hybrid", hint: "Weighted blend of popularity + content + CF." },
  { id: "collaborative", label: "Collaborative", hint: "Item-item CF on your rating history." },
  { id: "content", label: "Content-based", hint: "TF-IDF cosine similarity to your seed titles." },
  { id: "popularity", label: "Popularity", hint: "Bayesian-weighted top rated across the corpus." },
];

export default function Personalized() {
  const { userId } = useUser();
  const [strategy, setStrategy] = useState<Strategy>("hybrid");
  const [topK, setTopK] = useState(20);
  const recs = useForUser(userId, strategy, topK);
  const active = STRATS.find((s) => s.id === strategy)!;

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">For user {userId}</h1>
        <p className="muted text-sm">
          Personalized ranking from the {active.label} recommender.{" "}
          {active.hint}
        </p>
      </header>

      <div className="card flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2">
          {STRATS.map((s) => (
            <button
              key={s.id}
              onClick={() => setStrategy(s.id)}
              className={`chip ${strategy === s.id ? "chip-active" : ""}`}
              title={s.hint}
            >
              {s.label}
            </button>
          ))}
        </div>
        <label className="ml-auto flex items-center gap-2 text-sm">
          <span className="muted">Top-K</span>
          <input
            type="number"
            min={5}
            max={100}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value) || 20)}
            className="input !w-24 !py-1"
          />
        </label>
      </div>

      {recs.isLoading ? <LoadingSkeleton rows={4} /> : null}
      {recs.error ? (
        <ErrorState
          title="Recommendations unavailable"
          message={(recs.error as Error).message}
          onRetry={() => recs.refetch()}
        />
      ) : null}
      {recs.data && recs.data.items.length === 0 ? (
        <EmptyState
          title="Nothing to show yet"
          message={
            recs.data.personalized
              ? "The selected strategy returned no candidates for this user."
              : "Cold-start user. Try the onboarding flow or add a few ratings."
          }
        />
      ) : null}
      {recs.data && recs.data.items.length > 0 ? (
        <>
          {recs.data.notes && recs.data.notes.length > 0 ? (
            <div className="card border-slate-700 bg-bg text-xs text-slate-400">
              <div className="mb-1 font-semibold">Notes</div>
              <ul className="list-disc space-y-1 pl-5">
                {recs.data.notes.map((n, i) => (
                  <li key={i}>{n}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <RecommendationGrid items={recs.data.items} />
        </>
      ) : null}
    </section>
  );
}
