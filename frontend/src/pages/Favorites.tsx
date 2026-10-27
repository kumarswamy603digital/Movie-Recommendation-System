import { Link } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import { useFavorites, useMovie, useToggleFavorite } from "../api/queries";
import { MovieCard } from "../components/movie";
import { ErrorState, LoadingSkeleton, EmptyState } from "../components/ui";

function FavoriteRow({ user_id, movie_id }: { user_id: number; movie_id: number }) {
  const movie = useMovie(movie_id);
  const toggle = useToggleFavorite(user_id);
  if (movie.isLoading) return <LoadingSkeleton rows={1} />;
  if (movie.error) return <ErrorState message={(movie.error as Error).message} />;
  if (!movie.data) return null;
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1">
        <MovieCard movie={movie.data} />
      </div>
      <button
        className="btn-ghost"
        onClick={() => toggle.mutate({ movie_id, add: false })}
        disabled={toggle.isPending}
      >
        Remove
      </button>
    </div>
  );
}

export default function Favorites() {
  const { userId } = useUser();
  const favs = useFavorites(userId);
  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">Favorites · user {userId}</h1>
        <p className="muted text-sm">
          Saved titles that you can revisit; the hybrid recommender treats them
          as soft positive signals.
        </p>
      </header>
      {favs.isLoading ? <LoadingSkeleton rows={3} /> : null}
      {favs.error ? (
        <ErrorState message={(favs.error as Error).message} onRetry={() => favs.refetch()} />
      ) : null}
      {favs.data && favs.data.length === 0 ? (
        <EmptyState
          title="No favorites yet"
          message="Add titles from the Discover page or a movie's detail view."
          action={
            <Link to="/discover" className="btn-primary mt-2">
              Browse catalogue
            </Link>
          }
        />
      ) : null}
      {favs.data && favs.data.length > 0 ? (
        <div className="space-y-3">
          {favs.data.map((f) => (
            <FavoriteRow key={f.movie_id} user_id={userId} movie_id={f.movie_id} />
          ))}
        </div>
      ) : null}
    </section>
  );
}
