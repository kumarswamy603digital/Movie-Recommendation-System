// Smoke tests. They verify:
//   1. App mounts and shows header nav.
//   2. MovieCard renders title/year/rating from a fixture.
//   3. RecommendationCard exposes score + reasons.
//   4. RatingControl calls back with the clicked value.

import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import App from "../App";
import { MovieCard, RecommendationCard } from "../components/movie";
import { RatingControl } from "../components/RatingControl";
import { resetMocks, mockOnce } from "./mockFetch";

function withProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => resetMocks());

describe("App shell", () => {
  it("renders nav links and the primary header", () => {
    mockOnce("http://localhost:8000/api/v1/ready", {
      status: "ok",
      readiness: { api_process: true },
    });
    render(withProviders(<App />));
    expect(screen.getByRole("link", { name: /Home/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Discover/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Insights/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Find your next film/i })).toBeInTheDocument();
  });
});

describe("MovieCard", () => {
  it("shows title, year, mean rating and genres", () => {
    render(
      withProviders(
        <MovieCard
          movie={{
            movie_id: 1,
            title: "Toy Story",
            release_year: 1995,
            genres: ["Animation", "Children"],
            rating_count: 400,
            mean_rating: 4.35,
          }}
        />,
      ),
    );
    expect(screen.getByText(/Toy Story/i)).toBeInTheDocument();
    expect(screen.getByText(/1995/)).toBeInTheDocument();
    expect(screen.getByText(/4\.35/)).toBeInTheDocument();
    expect(screen.getByText(/Animation/)).toBeInTheDocument();
  });
});

describe("RecommendationCard", () => {
  it("shows score + component breakdown + reason list", () => {
    render(
      withProviders(
        <RecommendationCard
          rec={{
            movie: {
              movie_id: 42,
              title: "Dark City",
              release_year: 1998,
              genres: ["Sci-Fi"],
              rating_count: 12,
              mean_rating: 3.9,
            },
            score: 0.712,
            reasons: [{ kind: "content", text: "Similar genres to your seeds." }],
            component_scores: { popularity: 0.4, content: 0.62, cf: 0.05 },
          }}
        />,
      ),
    );
    expect(screen.getByText(/Dark City/i)).toBeInTheDocument();
    expect(screen.getByText(/0\.712/)).toBeInTheDocument();
    expect(screen.getByText(/content/i)).toBeInTheDocument();
  });
});

describe("RatingControl", () => {
  it("invokes onChange with the clicked value", () => {
    let picked: number | null = null;
    render(
      <RatingControl
        value={null}
        onChange={(n) => {
          picked = n;
        }}
      />,
    );
    fireEvent.click(screen.getByRole("radio", { name: "4" }));
    expect(picked).toBe(4);
  });
});
