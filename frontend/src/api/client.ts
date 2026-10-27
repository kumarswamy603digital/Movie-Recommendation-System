// Thin typed fetch wrapper around the FastAPI backend.
// All URLs are prefixed with /api/v1 as registered by main.py.

import type {
  AnalyticsOverview,
  ExplanationResponse,
  FavoriteOut,
  ModelComparison,
  MoviePage,
  MovieWithStats,
  PreferenceOut,
  PreferenceUpdate,
  RatingCreate,
  RatingOut,
  ReadyResponse,
  RecommendationList,
  RecommendationRequest,
  Genre,
} from "../types/api";

export const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export const V1 = `${API_BASE}/api/v1`;
export const DEMO_USER_ID = Number(import.meta.env.VITE_DEMO_USER_ID ?? "1") || 1;

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: unknown;
  constructor(message: string, status: number, code?: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${V1}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (res.status === 204) return null as T;
  const text = await res.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    /* keep raw text below */
  }
  if (!res.ok) {
    const body = parsed as
      | { error?: { code?: string; message?: string; details?: unknown }; detail?: unknown }
      | null;
    const msg =
      body?.error?.message ??
      (typeof body?.detail === "string" ? body.detail : undefined) ??
      (text || `HTTP ${res.status}`);
    throw new ApiError(msg, res.status, body?.error?.code, body?.error?.details ?? body?.detail);
  }
  return parsed as T;
}

export interface ListMoviesParams {
  q?: string;
  genre?: string;
  year_min?: number;
  year_max?: number;
  page?: number;
  page_size?: number;
  sort?: "popularity" | "rating" | "title" | "year";
}

function qs(params: Record<string, unknown> | undefined): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),
  ready: () => request<ReadyResponse>("/ready"),

  listMovies: (p: ListMoviesParams = {}) => request<MoviePage>(`/movies${qs(p)}`),
  searchMovies: (q: string, page = 1, page_size = 25) =>
    request<MoviePage>(`/movies/search${qs({ q, page, page_size })}`),
  getMovie: (id: number) => request<MovieWithStats>(`/movies/${id}`),
  listGenres: () => request<Genre[]>("/genres"),

  popular: (user_id: number | null, top_k = 20) =>
    request<RecommendationList>(`/recommendations/popular${qs({ user_id, top_k })}`),
  similar: (movie_id: number, top_k = 20) =>
    request<RecommendationList>(`/recommendations/similar/${movie_id}${qs({ top_k })}`),
  forUser: (user_id: number, strategy: string, top_k = 20) =>
    request<RecommendationList>(
      `/recommendations/users/${user_id}${qs({ strategy, top_k })}`,
    ),
  recommend: (body: RecommendationRequest) =>
    request<RecommendationList>("/recommendations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  explain: (movie_id: number, user_id: number | null) =>
    request<ExplanationResponse>(`/recommendations/explanations/${movie_id}${qs({ user_id })}`),

  putRating: (body: RatingCreate) =>
    request<RatingOut>("/ratings", { method: "POST", body: JSON.stringify(body) }),
  listRatings: (user_id: number) => request<RatingOut[]>(`/users/${user_id}/ratings`),

  addFavorite: (user_id: number, movie_id: number) =>
    request<FavoriteOut>(`/users/${user_id}/favorites`, {
      method: "POST",
      body: JSON.stringify({ movie_id }),
    }),
  removeFavorite: (user_id: number, movie_id: number) =>
    request<void>(`/users/${user_id}/favorites/${movie_id}`, { method: "DELETE" }),
  listFavorites: (user_id: number) => request<FavoriteOut[]>(`/users/${user_id}/favorites`),

  putPreferences: (user_id: number, body: PreferenceUpdate) =>
    request<PreferenceOut>(`/users/${user_id}/preferences`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),
  getPreferences: (user_id: number) =>
    request<PreferenceOut>(`/users/${user_id}/preferences`),

  overview: () => request<AnalyticsOverview>("/analytics/overview"),
  modelComparison: () => request<ModelComparison>("/analytics/model-comparison"),
};
