// Reusable UI atoms. Kept minimal — Tailwind classes and small variations only.

import type { ReactNode } from "react";

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-live="polite">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-16 w-full animate-pulse rounded-lg bg-surface" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-center justify-center gap-2 py-10 text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      {message ? <p className="muted max-w-lg text-sm">{message}</p> : null}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="card border-red-900/60 bg-red-950/30 text-red-100"
    >
      <h3 className="text-lg font-semibold">{title}</h3>
      {message ? <p className="mt-1 text-sm">{message}</p> : null}
      {onRetry ? (
        <button onClick={onRetry} className="btn-ghost mt-3 self-start">
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function Pagination({
  page,
  page_size,
  total,
  onChange,
}: {
  page: number;
  page_size: number;
  total: number;
  onChange: (p: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / page_size));
  const prev = () => onChange(Math.max(1, page - 1));
  const next = () => onChange(Math.min(pages, page + 1));
  return (
    <div className="mt-4 flex items-center justify-between text-sm">
      <span className="muted">
        Page {page} of {pages} · {total} results
      </span>
      <div className="flex gap-2">
        <button className="btn-ghost" onClick={prev} disabled={page <= 1}>
          Previous
        </button>
        <button className="btn-ghost" onClick={next} disabled={page >= pages}>
          Next
        </button>
      </div>
    </div>
  );
}

export function GenreFilter({
  genres,
  value,
  onChange,
}: {
  genres: string[];
  value: string | null;
  onChange: (g: string | null) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <button
        className={`chip ${value === null ? "chip-active" : ""}`}
        onClick={() => onChange(null)}
      >
        All
      </button>
      {genres.map((g) => (
        <button
          key={g}
          className={`chip ${value === g ? "chip-active" : ""}`}
          onClick={() => onChange(g)}
        >
          {g}
        </button>
      ))}
    </div>
  );
}

export function SearchBar({
  value,
  onChange,
  placeholder = "Search titles…",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      className="input"
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Search movies"
    />
  );
}
