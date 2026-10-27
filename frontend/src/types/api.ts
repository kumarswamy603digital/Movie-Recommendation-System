// Mirrors backend Pydantic schemas in PROJECT2/backend/app/schemas/schemas.py.
// Keep in sync. If the backend adds or renames a field, update this file too.

export interface Movie {
  movie_id: number;
  title: string;
  release_year: number | null;
  genres: string[];
  tmdb_id?: number | null;
  poster_url?: string | null;
  overview?: string | null;
}

export interface MovieWithStats extends Movie {
  rating_count: number;
  mean_rating: number;
}

export interface MoviePage {
  items: MovieWithStats[];
  total: number;
  page: number;
  page_size: number;
}

export interface Genre {
  name: string;
  movie_count: number;
}

export type ReasonKind =
  | "content"
  | "collaborative"
  | "popularity"
  | "hybrid"
  | "onboarding";

export interface RecommendationReason {
  kind: ReasonKind;
  text: string;
}

export interface RecommendedMovie {
  movie: MovieWithStats;
  score: number;
  reasons: RecommendationReason[];
  component_scores: Record<string, number>;
}

export interface RecommendationList {
  strategy: string;
  user_id: number | null;
  based_on_movie_id: number | null;
  items: RecommendedMovie[];
  personalized: boolean;
  notes: string[];
}

export interface RatingOut {
  user_id: number;
  movie_id: number;
  value: number;
  updated_at: string;
}

export interface RatingCreate {
  user_id: number;
  movie_id: number;
  value: number;
}

export interface FavoriteOut {
  user_id: number;
  movie_id: number;
  created_at: string;
}

export interface PreferenceOut {
  user_id: number;
  genres: string[];
  seed_movie_ids: number[];
  updated_at: string;
}

export interface PreferenceUpdate {
  genres: string[];
  seed_movie_ids: number[];
}

export interface RecommendationRequest {
  user_id: number;
  strategy?: "hybrid" | "popularity" | "content" | "collaborative";
  top_k?: number;
  genres?: string[] | null;
  year_min?: number | null;
  year_max?: number | null;
  exclude_rated?: boolean;
}

export interface DatasetSummary {
  dataset_version: string;
  n_users: number;
  n_movies: number;
  n_ratings: number;
  n_genres: number;
  missing_values: Record<string, number>;
  processed_at?: string | null;
}

export interface ModelMetrics {
  model: string;
  evaluation_date?: string | null;
  top_k?: number | null;
  precision_at_k?: number | null;
  recall_at_k?: number | null;
  ndcg_at_k?: number | null;
  coverage?: number | null;
  rmse?: number | null;
  mae?: number | null;
  notes?: string | null;
}

export interface AnalyticsOverview {
  dataset: DatasetSummary | null;
  model_version: string | null;
  n_fitted_users: number | null;
  n_catalog_movies: number | null;
}

export interface ModelComparison {
  protocol: string;
  top_k: number;
  metrics: ModelMetrics[];
}

export interface ReadyResponse {
  status: "ok" | "degraded";
  readiness: Record<string, boolean>;
}

export interface ExplanationResponse {
  movie_id: number;
  user_id: number | null;
  personalized: boolean;
  reasons: RecommendationReason[];
}

export interface ApiErrorShape {
  error?: { code?: string; message?: string; details?: unknown };
  detail?: unknown;
}
