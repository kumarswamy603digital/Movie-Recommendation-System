# Frontend

React 18 + Vite + TypeScript + Tailwind 3 + React Router 6 + TanStack
Query 5 + Recharts. Dark cinematic theme (`bg = #0b0d10`, `surface =
#12161c`, `accent = #e50914`).

## Requires

- Node.js ≥ 20. If not installed on Windows:
  `winget install OpenJS.NodeJS.LTS` (admin).

## Develop

```powershell
cd PROJECT2\frontend
copy .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:5173`. Backend must be running on
`http://localhost:8000` (see root README Quickstart).

## Env

| Var | Default | Purpose |
|-----|---------|---------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Where `api/client.ts` points; no trailing slash |
| `VITE_DEMO_USER_ID` | `1` | Initial user id when localStorage has none |

## Pages

| Route | Component | What it does |
|-------|-----------|--------------|
| `/` | `Home` | Hero + Bayesian-popularity strip |
| `/discover` | `Discover` | Search, genre chips, sort, paginated grid |
| `/movies/:id` | `MovieDetails` | Movie stats, rating control, favorite toggle, "why this appears", similar titles |
| `/for-you` | `Personalized` | Four strategy chips + top-K slider; renders component scores and reasons |
| `/onboarding` | `Onboarding` | Genre picker + seed-movie search; saves preferences |
| `/favorites` | `Favorites` | Lists favorited movies with remove action |
| `/ratings` | `MyRatings` | Reverse-chronological list of the user's saved ratings |
| `/insights` | `ModelInsights` | Renders real evaluation metrics from `/analytics/model-comparison` (Recharts bar chart + table) |
| `/about` | `About` | Plain-language method + limitations |

## Build

```powershell
npm run build         # tsc --noEmit && vite build  → dist/
npm run preview       # serve dist/ for smoke testing
```

## Test

```powershell
npm run test:run      # vitest run — smoke suite in src/test/app.test.tsx
```

Test files use a lightweight `fetch` mock (`src/test/mockFetch.ts`) so they
never hit the network.

## Structure notes

- `src/api/client.ts` is a plain `fetch` wrapper — swap to `axios` if you
  need request/response interceptors for auth later.
- `src/api/queries.ts` centralises all TanStack Query keys via `keys.*` so
  `invalidateQueries(["recs"])` after a rating mutation cleanly refreshes
  recommendation pages without key drift.
- `src/hooks/useUser.ts` reads/writes `mr.user_id` in `localStorage`; the
  Layout's header exposes an editable numeric field so you can impersonate
  any MovieLens user during a demo.
- Tailwind utility classes live in `src/index.css` under `@layer
  components`: `.btn-primary`, `.btn-ghost`, `.card`, `.input`, `.chip`,
  `.chip-active`, `.muted`.
- Every page uses `ErrorState` / `LoadingSkeleton` / `EmptyState` from
  `components/ui.tsx` — the app never shows a spinner with no message or a
  blank screen on failure.

## Known limitations

- Not executed on the dev machine (Node not installed). Types align
  exactly with `PROJECT2/backend/app/schemas/schemas.py`.
- No auth flow — the frontend trusts `user_id`. Documented as a demo shim.
- Recharts responsive width relies on the parent having an explicit height;
  the Insights chart sits in a `h-72` wrapper for that reason.
