import { Link } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import { useMovie, useRatings } from "../api/queries";
import { ErrorState, LoadingSkeleton, EmptyState } from "../components/ui";
import type { RatingOut } from "../types/api";

function RatedRow({ user_id, rating }: { user_id: number; rating: RatingOut }) {
  const movie = useMovie(rating.movie_id);
  return (
    <div className="card flex items-center justify-between gap-3 text-sm">
      <div className="min-w-0 flex-1">
        {movie.isLoading ? <LoadingSkeleton rows={1} /> : null}
        {movie.error ? (
          <ErrorState message={(movie.error as Error).message} />
        ) : null}
        {movie.data ? (
          <>
            <Link to={`/movies/${movie.data.movie_id}`} className="font-semibold hover:underline">
              {movie.data.title}
            </Link>
            <div className="muted text-xs">
              {movie.data.release_year ?? "—"} · {movie.data.genres.slice(0, 3).join(", ")}
            </div>
          </>
        ) : null}
      </div>
      <div className="text-right">
        <div className="text-lg font-semibold">{rating.value} / 5</div>
        <div className="muted text-xs">
          {new Date(rating.updated_at).toLocaleDateString()}
        </div>
      </div>
      <span className="muted text-xs">user {user_id}</span>
    </div>
  );
}

export default function MyRatings() {
  const { userId } = useUser();
  const ratings = useRatings(userId);
  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">My ratings · user {userId}</h1>
        <p className="muted text-sm">
          Ratings saved on this device. Collaborative filtering uses these to
          build your neighbourhood.
        </p>
      </header>
      {ratings.isLoading ? <LoadingSkeleton rows={3} /> : null}
      {ratings.error ? (
        <ErrorState message={(ratings.error as Error).message} onRetry={() => ratings.refetch()} />
      ) : null}
      {ratings.data && ratings.data.length === 0 ? (
        <EmptyState
          title="No ratings yet"
          message="Head to a movie's detail page to leave one."
          action={
            <Link to="/discover" className="btn-primary mt-2">
              Find a movie
            </Link>
          }
        />
      ) : null}
      {ratings.data && ratings.data.length > 0 ? (
        <div className="space-y-2">
          {ratings.data.map((r) => (
            <RatedRow key={r.movie_id} user_id={userId} rating={r} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
