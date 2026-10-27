import { useEffect, useMemo, useState } from "react";
import { useGenres, useMovies } from "../api/queries";
import { MovieGrid } from "../components/movie";
import {
  ErrorState,
  GenreFilter,
  LoadingSkeleton,
  Pagination,
  SearchBar,
} from "../components/ui";

export default function Discover() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [genre, setGenre] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<"popularity" | "rating" | "title" | "year">(
    "popularity",
  );
  const pageSize = 24;

  // Debounce text input by 250ms; reset paging on filter changes.
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(q), 250);
    return () => window.clearTimeout(id);
  }, [q]);
  useEffect(() => {
    setPage(1);
  }, [debounced, genre, sort]);

  const genres = useGenres();
  const params = useMemo(
    () => ({
      q: debounced || undefined,
      genre: genre ?? undefined,
      page,
      page_size: pageSize,
      sort,
    }),
    [debounced, genre, page, sort],
  );
  const movies = useMovies(params);

  return (
    <section className="space-y-4">
      <header>
        <h1 className="text-2xl font-bold">Discover</h1>
        <p className="muted text-sm">
          Search, filter and sort across the {movies.data?.total ?? "…"} films
          with rating data in the offline catalogue.
        </p>
      </header>

      <div className="card space-y-3">
        <SearchBar
          value={q}
          onChange={setQ}
          placeholder="Search titles (e.g. 'alien')"
        />
        {genres.data ? (
          <GenreFilter
            genres={genres.data.map((g) => g.name)}
            value={genre}
            onChange={setGenre}
          />
        ) : null}
        <div className="flex items-center gap-3 text-sm">
          <label className="muted">Sort</label>
          <select
            className="input !w-40 !py-1"
            value={sort}
            onChange={(e) => setSort(e.target.value as typeof sort)}
          >
            <option value="popularity">Popularity</option>
            <option value="rating">Rating</option>
            <option value="title">Title</option>
            <option value="year">Year</option>
          </select>
        </div>
      </div>

      {movies.isLoading ? <LoadingSkeleton rows={4} /> : null}
      {movies.error ? (
        <ErrorState
          title="Catalogue unavailable"
          message={(movies.error as Error).message}
          onRetry={() => movies.refetch()}
        />
      ) : null}
      {movies.data ? (
        <>
          <MovieGrid movies={movies.data.items} cols={4} />
          <Pagination
            page={movies.data.page}
            page_size={movies.data.page_size}
            total={movies.data.total}
            onChange={setPage}
          />
        </>
      ) : null}
    </section>
  );
}
