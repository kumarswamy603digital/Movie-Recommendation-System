import { Link } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import { useForUser, useMovies, usePopular } from "../api/queries";
import { MovieCarousel, RecommendationGrid } from "../components/movie";
import { ErrorState, LoadingSkeleton, EmptyState } from "../components/ui";

// Home layout follows spec §10.A:
//   - Cinematic hero featuring a movie selected from real data (top-1
//     Bayesian-popularity title from the API — never hardcoded).
//   - Trending rail, clearly labelled with its ranking method.
//   - Personalized rail when the user has preferences or history.
//   - Genre-based discovery rails (3 fixed genre samples).

const DISCOVERY_GENRES = ["Sci-Fi", "Comedy", "Drama"] as const;

export default function Home() {
  const { userId } = useUser();
  const popular = usePopular(userId, 20);
  const forYou = useForUser(userId, "hybrid", 12);

  const hero = popular.data?.items[0]?.movie ?? null;
  const trending = (popular.data?.items ?? []).slice(0, 12).map((r) => r.movie);

  return (
    <section className="space-y-6">
      {/* Hero */}
      <div className="card relative overflow-hidden !bg-gradient-to-br from-surface via-bg to-bg">
        {popular.isLoading ? (
          <LoadingSkeleton rows={3} />
        ) : hero ? (
          <>
            <div className="absolute inset-0 -z-0 opacity-30 [background:radial-gradient(circle_at_80%_20%,#e50914_0%,transparent_60%)]" />
            <div className="relative z-10 flex flex-wrap items-start justify-between gap-6">
              <div className="max-w-2xl">
                <div className="muted text-xs uppercase tracking-widest">
                  Now trending · Bayesian weighted rating
                </div>
                <h1 className="mt-2 text-3xl font-bold md:text-4xl">
                  {hero.title}
                </h1>
                <div className="muted mt-1 text-sm">
                  {hero.release_year ?? "—"} ·{" "}
                  <span className="text-white">
                    {hero.mean_rating.toFixed(2)}
                  </span>{" "}
                  / 5 · {hero.rating_count} ratings ·{" "}
                  {hero.genres.slice(0, 3).join(", ")}
                </div>
                <p className="mt-3 max-w-xl text-sm text-slate-300">
                  An ML-driven discovery experience on top of the MovieLens
                  catalogue. Four recommender strategies — popularity,
                  content-based (TF-IDF cosine), item-item collaborative
                  filtering, and a normalised hybrid — sit behind one
                  interface. Every number on the Insights page comes from a
                  real offline evaluation.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link to={`/movies/${hero.movie_id}`} className="btn-primary">
                    View details
                  </Link>
                  <Link to="/discover" className="btn-ghost">
                    Browse catalogue
                  </Link>
                  <Link to="/for-you" className="btn-ghost">
                    Personalized picks
                  </Link>
                  <Link to="/onboarding" className="btn-ghost">
                    Set preferences
                  </Link>
                  <Link to="/insights" className="btn-ghost">
                    Model metrics
                  </Link>
                </div>
              </div>
            </div>
          </>
        ) : (
          <EmptyState
            title="No hero available"
            message="Popularity recommender returned nothing. Run train_models.py first."
          />
        )}
      </div>

      {popular.error ? (
        <ErrorState
          title="Backend offline?"
          message={(popular.error as Error).message}
          onRetry={() => popular.refetch()}
        />
      ) : null}

      {/* Trending rail */}
      {trending.length > 0 ? (
        <MovieCarousel
          title="Trending now"
          subtitle={`Bayesian weighted rating · user ${userId ?? "—"} excludes rated titles`}
          movies={trending}
        />
      ) : null}

      {/* Personalized rail — appears only if hybrid actually has signals */}
      {forYou.data && forYou.data.personalized && forYou.data.items.length > 0 ? (
        <div>
          <div className="mb-3 flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">Recommended for you</h2>
            <span className="muted text-xs">
              Hybrid · pop + content + CF blend (personalized=true)
            </span>
          </div>
          <RecommendationGrid items={forYou.data.items.slice(0, 6)} />
        </div>
      ) : (
        <div className="card text-sm">
          <div className="mb-1 font-semibold">Not personalized yet</div>
          <p className="muted">
            We don't fake personalization. Rate a few titles or complete the
            onboarding flow to unlock the recommended-for-you rail.
          </p>
          <Link to="/onboarding" className="btn-primary mt-3 inline-flex">
            Set preferences
          </Link>
        </div>
      )}

      {/* Genre discovery rails */}
      {DISCOVERY_GENRES.map((g) => (
        <GenreRail key={g} genre={g} />
      ))}
    </section>
  );
}

function GenreRail({ genre }: { genre: string }) {
  const rail = useMovies({ genre, page_size: 12, sort: "rating", page: 1 });
  if (rail.isLoading) return <LoadingSkeleton rows={1} />;
  if (!rail.data || rail.data.items.length === 0) return null;
  return (
    <MovieCarousel
      title={genre}
      subtitle="Top rated within the genre"
      movies={rail.data.items}
    />
  );
}
