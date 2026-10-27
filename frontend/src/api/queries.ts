// TanStack Query hooks. Each hook wraps one endpoint and exposes
// conventional `data / isLoading / error / refetch` fields.

import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, type ListMoviesParams } from "./client";
import type {
  RatingCreate,
  RecommendationRequest,
  PreferenceUpdate,
} from "../types/api";

export const keys = {
  movies: (p: ListMoviesParams) => ["movies", p] as const,
  movie: (id: number) => ["movie", id] as const,
  genres: () => ["genres"] as const,
  popular: (uid: number | null, k: number) => ["recs", "popular", uid, k] as const,
  similar: (mid: number, k: number) => ["recs", "similar", mid, k] as const,
  forUser: (uid: number, strat: string, k: number) =>
    ["recs", "user", uid, strat, k] as const,
  ratings: (uid: number) => ["ratings", uid] as const,
  favorites: (uid: number) => ["favorites", uid] as const,
  preferences: (uid: number) => ["preferences", uid] as const,
  explain: (mid: number, uid: number | null) => ["explain", mid, uid] as const,
  overview: () => ["analytics", "overview"] as const,
  comparison: () => ["analytics", "comparison"] as const,
  ready: () => ["system", "ready"] as const,
};

export function useReady() {
  return useQuery({ queryKey: keys.ready(), queryFn: api.ready, staleTime: 30_000 });
}

export function useGenres() {
  return useQuery({ queryKey: keys.genres(), queryFn: api.listGenres, staleTime: 300_000 });
}

export function useMovies(params: ListMoviesParams) {
  return useQuery({
    queryKey: keys.movies(params),
    queryFn: () => api.listMovies(params),
    placeholderData: keepPreviousData,
  });
}

export function useMovie(id: number | null) {
  return useQuery({
    queryKey: keys.movie(id ?? -1),
    queryFn: () => api.getMovie(id as number),
    enabled: id != null && id > 0,
  });
}

export function usePopular(user_id: number | null, top_k = 20) {
  return useQuery({
    queryKey: keys.popular(user_id, top_k),
    queryFn: () => api.popular(user_id, top_k),
  });
}

export function useSimilar(movie_id: number | null, top_k = 12) {
  return useQuery({
    queryKey: keys.similar(movie_id ?? -1, top_k),
    queryFn: () => api.similar(movie_id as number, top_k),
    enabled: movie_id != null && movie_id > 0,
  });
}

export function useForUser(user_id: number, strategy: string, top_k = 20) {
  return useQuery({
    queryKey: keys.forUser(user_id, strategy, top_k),
    queryFn: () => api.forUser(user_id, strategy, top_k),
  });
}

export function useRecommendation(body: RecommendationRequest, enabled = true) {
  return useQuery({
    queryKey: [
      "recs",
      "post",
      body.user_id,
      body.strategy,
      body.top_k,
      body.genres ?? null,
      body.year_min ?? null,
      body.year_max ?? null,
      body.exclude_rated,
    ],
    queryFn: () => api.recommend(body),
    enabled,
  });
}

export function useExplain(movie_id: number | null, user_id: number | null) {
  return useQuery({
    queryKey: keys.explain(movie_id ?? -1, user_id),
    queryFn: () => api.explain(movie_id as number, user_id),
    enabled: movie_id != null && movie_id > 0,
  });
}

export function useRatings(user_id: number) {
  return useQuery({ queryKey: keys.ratings(user_id), queryFn: () => api.listRatings(user_id) });
}

export function useFavorites(user_id: number) {
  return useQuery({ queryKey: keys.favorites(user_id), queryFn: () => api.listFavorites(user_id) });
}

export function usePreferences(user_id: number) {
  return useQuery({
    queryKey: keys.preferences(user_id),
    queryFn: () => api.getPreferences(user_id),
  });
}

export function usePutRating() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RatingCreate) => api.putRating(body),
    onSuccess: (_data, body) => {
      qc.invalidateQueries({ queryKey: keys.ratings(body.user_id) });
      qc.invalidateQueries({ queryKey: ["recs"] });
      qc.invalidateQueries({ queryKey: keys.movie(body.movie_id) });
    },
  });
}

export function useToggleFavorite(user_id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ movie_id, add }: { movie_id: number; add: boolean }) =>
      add ? api.addFavorite(user_id, movie_id) : api.removeFavorite(user_id, movie_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.favorites(user_id) });
    },
  });
}

export function usePutPreferences(user_id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PreferenceUpdate) => api.putPreferences(user_id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.preferences(user_id) });
      qc.invalidateQueries({ queryKey: ["recs"] });
    },
  });
}

export function useOverview() {
  return useQuery({ queryKey: keys.overview(), queryFn: api.overview });
}

export function useModelComparison() {
  return useQuery({ queryKey: keys.comparison(), queryFn: api.modelComparison });
}
