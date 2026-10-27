import { Link, useParams } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import {
  useExplain,
  useFavorites,
  useMovie,
  usePutRating,
  useRatings,
  useSimilar,
  useToggleFavorite,
} from "../api/queries";
import { RecommendationGrid, GenreChips } from "../components/movie";
import { ErrorState, LoadingSkeleton, EmptyState } from "../components/ui";
import { RatingControl } from "../components/RatingControl";

export default function MovieDetails() {
  const { id } = useParams();
  const movieId = Number(id ?? "0");
  const { userId } = useUser();
  const movie = useMovie(movieId);
  const similar = useSimilar(movieId, 8);
  const explain = useExplain(movieId, userId);
  const myFavs = useFavorites(userId);
  const myRatings = useRatings(userId);
  const putRating = usePutRating();
  const toggleFav = useToggleFavorite(userId);

  if (!movieId || Number.isNaN(movieId)) {
    return <ErrorState title="Bad movie id" />;
  }

  const isFav = (myFavs.data ?? []).some((f) => f.movie_id === movieId);
  const myRating = (myRatings.data ?? []).find((r) => r.movie_id === movieId)?.value ?? null;

  return (
    <section className="space-y-6">
      {movie.isLoading ? <LoadingSkeleton rows={3} /> : null}
      {movie.error ? (
        <ErrorState
          title="Movie not found"
          message={(movie.error as Error).message}
          onRetry={() => movie.refetch()}
        />
      ) : null}
      {movie.data ? (
        <div className="card space-y-4">
          <div className="flex flex-wrap items-baseline gap-3">
            <h1 className="text-2xl font-bold">{movie.data.title}</h1>
            <span className="muted">
              {movie.data.release_year ?? "—"} · {movie.data.rating_count} ratings
            </span>
            <span className="ml-auto text-lg font-semibold">
              {movie.data.mean_rating.toFixed(2)}
              <span className="muted text-sm"> / 5</span>
            </span>
          </div>
          <GenreChips genres={movie.data.genres} max={18} />
          <div>
            <div className="mb-2 text-sm font-semibold">Your rating</div>
            <RatingControl
              value={myRating}
              disabled={putRating.isPending}
              onChange={(n) =>
                putRating.mutate({ user_id: userId, movie_id: movieId, value: n })
              }
            />
            {putRating.error ? (
              <p className="mt-2 text-xs text-red-400">
                {(putRating.error as Error).message}
              </p>
            ) : null}
            {putRating.isSuccess ? (
              <p className="mt-2 text-xs text-emerald-400">
                Saved rating {putRating.data?.value}.
              </p>
            ) : null}
          </div>
          <div className="flex gap-2">
            <button
              className="btn-ghost"
              onClick={() => toggleFav.mutate({ movie_id: movieId, add: !isFav })}
              disabled={toggleFav.isPending}
            >
              {isFav ? "★ Favorited" : "☆ Add to favorites"}
            </button>
            <Link to={`/discover?genre=${movie.data.genres[0] ?? ""}`} className="btn-ghost">
              More {movie.data.genres[0] ?? "movies"}
            </Link>
          </div>
          {explain.data && explain.data.reasons.length > 0 ? (
            <div className="mt-4">
              <div className="mb-2 text-sm font-semibold">Why this appears</div>
              <ul className="space-y-1 text-xs text-slate-400">
                {explain.data.reasons.map((r, i) => (
                  <li key={i}>
                    <span className="rounded bg-bg px-1.5 py-0.5 text-[10px] uppercase">
                      {r.kind}
                    </span>{" "}
                    {r.text}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <div>
        <h2 className="mb-3 text-lg font-semibold">Similar titles</h2>
        {similar.isLoading ? <LoadingSkeleton rows={2} /> : null}
        {similar.error ? (
          <ErrorState message={(similar.error as Error).message} />
        ) : null}
        {similar.data && similar.data.items.length === 0 ? (
          <EmptyState
            title="No similar titles yet"
            message="Content-based index has not been fitted."
          />
        ) : null}
        {similar.data && similar.data.items.length > 0 ? (
          <RecommendationGrid items={similar.data.items} />
        ) : null}
      </div>
    </section>
  );
}
