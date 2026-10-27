// Movie-specific presentational components.

import { Link } from "react-router-dom";
import type {
  MovieWithStats,
  RecommendedMovie,
  RecommendationReason,
} from "../types/api";

function formatYear(y: number | null | undefined): string {
  return y && y > 0 ? String(y) : "—";
}

export function GenreChips({ genres, max = 4 }: { genres: string[]; max?: number }) {
  const shown = genres.slice(0, max);
  const extra = genres.length - shown.length;
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((g) => (
        <span key={g} className="chip">
          {g}
        </span>
      ))}
      {extra > 0 ? <span className="chip">+{extra}</span> : null}
    </div>
  );
}

export function ReasonList({ reasons }: { reasons: RecommendationReason[] }) {
  if (!reasons || reasons.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1 text-xs text-slate-400">
      {reasons.map((r, i) => (
        <li key={i} className="flex gap-2">
          <span className="rounded bg-bg px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
            {r.kind}
          </span>
          <span>{r.text}</span>
        </li>
      ))}
    </ul>
  );
}

export function MovieCard({ movie }: { movie: MovieWithStats }) {
  return (
    <Link
      to={`/movies/${movie.movie_id}`}
      className="card flex h-full flex-col justify-between transition hover:border-accent"
    >
      <div>
        <div className="line-clamp-2 text-sm font-semibold">{movie.title}</div>
        <div className="muted text-xs">
          {formatYear(movie.release_year)} · {movie.rating_count} ratings
        </div>
        <div className="mt-2">
          <GenreChips genres={movie.genres} />
        </div>
      </div>
      <div className="mt-3 text-xs">
        <span className="font-semibold text-white">
          {movie.mean_rating.toFixed(2)}
        </span>
        <span className="muted"> / 5</span>
      </div>
    </Link>
  );
}

export function RecommendationCard({ rec }: { rec: RecommendedMovie }) {
  return (
    <div className="card flex h-full flex-col justify-between">
      <div>
        <Link
          to={`/movies/${rec.movie.movie_id}`}
          className="line-clamp-2 text-sm font-semibold hover:underline"
        >
          {rec.movie.title}
        </Link>
        <div className="muted text-xs">
          {formatYear(rec.movie.release_year)} · {rec.movie.rating_count} ratings
        </div>
        <div className="mt-2">
          <GenreChips genres={rec.movie.genres} />
        </div>
        <div className="mt-2 text-xs">
          <span className="muted">score </span>
          <span className="font-semibold">{rec.score.toFixed(3)}</span>
          {Object.keys(rec.component_scores || {}).length > 0 ? (
            <span className="muted ml-2">
              (
              {Object.entries(rec.component_scores)
                .map(([k, v]) => `${k}:${v.toFixed(2)}`)
                .join(" · ")}
              )
            </span>
          ) : null}
        </div>
        <ReasonList reasons={rec.reasons} />
      </div>
      <div className="mt-3">
        <Link
          to={`/movies/${rec.movie.movie_id}`}
          className="text-xs text-accent hover:underline"
        >
          View details →
        </Link>
      </div>
    </div>
  );
}

export function MovieGrid({
  movies,
  cols = 4,
}: {
  movies: MovieWithStats[];
  cols?: 3 | 4 | 5 | 6;
}) {
  const colClass =
    cols === 3
      ? "md:grid-cols-3"
      : cols === 5
      ? "md:grid-cols-5"
      : cols === 6
      ? "md:grid-cols-6"
      : "md:grid-cols-4";
  return (
    <div className={`grid grid-cols-2 gap-3 ${colClass}`}>
      {movies.map((m) => (
        <MovieCard key={m.movie_id} movie={m} />
      ))}
    </div>
  );
}

export function RecommendationGrid({ items }: { items: RecommendedMovie[] }) {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {items.map((r) => (
        <RecommendationCard key={r.movie.movie_id} rec={r} />
      ))}
    </div>
  );
}

// Horizontal scrollable rail. Uses native overflow so it degrades
// gracefully on touch devices without any JS. Height is fixed to keep
// aspect consistent across cards.
export function MovieCarousel({
  title,
  subtitle,
  movies,
}: {
  title: string;
  subtitle?: string;
  movies: MovieWithStats[];
}) {
  if (!movies || movies.length === 0) return null;
  return (
    <section aria-label={title}>
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        {subtitle ? <span className="muted text-xs">{subtitle}</span> : null}
      </div>
      <div
        className="flex gap-3 overflow-x-auto pb-2"
        style={{ scrollSnapType: "x mandatory" }}
      >
        {movies.map((m) => (
          <div
            key={m.movie_id}
            className="w-56 shrink-0"
            style={{ scrollSnapAlign: "start" }}
          >
            <MovieCard movie={m} />
          </div>
        ))}
      </div>
    </section>
  );
}
