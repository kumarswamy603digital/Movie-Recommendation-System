// Cold-start onboarding: pick favourite genres + a handful of seed movies,
// saved as PreferenceUpdate. Uses the search endpoint for seed picking.

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import {
  useGenres,
  useMovies,
  usePreferences,
  usePutPreferences,
} from "../api/queries";
import { ErrorState, LoadingSkeleton } from "../components/ui";

export default function Onboarding() {
  const { userId } = useUser();
  const navigate = useNavigate();
  const genres = useGenres();
  const prefs = usePreferences(userId);
  const save = usePutPreferences(userId);

  const [selectedGenres, setSelectedGenres] = useState<string[]>([]);
  const [seedIds, setSeedIds] = useState<number[]>([]);
  const [seedTitle, setSeedTitle] = useState("");
  const seeds = useMovies({ q: seedTitle, page_size: 6, sort: "popularity" });

  useEffect(() => {
    if (prefs.data) {
      setSelectedGenres(prefs.data.genres ?? []);
      setSeedIds(prefs.data.seed_movie_ids ?? []);
    }
  }, [prefs.data]);

  const toggleGenre = (g: string) =>
    setSelectedGenres((cur) =>
      cur.includes(g) ? cur.filter((x) => x !== g) : [...cur, g],
    );
  const toggleSeed = (id: number) =>
    setSeedIds((cur) =>
      cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id].slice(-10),
    );

  const submit = () => {
    save.mutate(
      { genres: selectedGenres, seed_movie_ids: seedIds },
      { onSuccess: () => navigate("/for-you") },
    );
  };

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">Cold-start preferences</h1>
        <p className="muted text-sm">
          Choose a few favourite genres and up to 10 seed films. Content-based
          and hybrid use these as the profile anchor until you rate titles
          directly.
        </p>
      </header>

      <div className="card space-y-3">
        <div className="text-sm font-semibold">Genres</div>
        {genres.isLoading ? <LoadingSkeleton rows={2} /> : null}
        {genres.error ? <ErrorState message={(genres.error as Error).message} /> : null}
        {genres.data ? (
          <div className="flex flex-wrap gap-2">
            {genres.data.map((g) => (
              <button
                key={g.name}
                onClick={() => toggleGenre(g.name)}
                className={`chip ${selectedGenres.includes(g.name) ? "chip-active" : ""}`}
              >
                {g.name}{" "}
                <span className="muted ml-1">({g.movie_count})</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="card space-y-3">
        <div className="text-sm font-semibold">
          Seed movies ({seedIds.length}/10)
        </div>
        <input
          className="input"
          placeholder="Search titles to seed your profile"
          value={seedTitle}
          onChange={(e) => setSeedTitle(e.target.value)}
        />
        {seeds.data ? (
          <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
            {seeds.data.items.map((m) => {
              const on = seedIds.includes(m.movie_id);
              return (
                <button
                  key={m.movie_id}
                  onClick={() => toggleSeed(m.movie_id)}
                  className={
                    "card text-left text-xs " +
                    (on ? "!border-accent" : "hover:border-slate-600")
                  }
                >
                  <div className="font-semibold">{m.title}</div>
                  <div className="muted">
                    {m.release_year ?? "—"} · {m.mean_rating.toFixed(2)} ·{" "}
                    {m.rating_count}
                  </div>
                </button>
              );
            })}
          </div>
        ) : null}
      </div>

      <div className="flex items-center gap-3">
        <button
          className="btn-primary"
          onClick={submit}
          disabled={save.isPending || (selectedGenres.length === 0 && seedIds.length === 0)}
        >
          Save & view picks
        </button>
        {save.error ? (
          <span className="text-xs text-red-400">{(save.error as Error).message}</span>
        ) : null}
        {save.isSuccess ? (
          <span className="text-xs text-emerald-400">Saved.</span>
        ) : null}
      </div>
    </section>
  );
}
