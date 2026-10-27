// App shell: sticky header with nav + demo user switcher, main outlet, footer.

import { Link, NavLink, Outlet } from "react-router-dom";
import { useUser } from "../hooks/useUser";
import { useReady } from "../api/queries";

const NAV = [
  { to: "/", label: "Home" },
  { to: "/discover", label: "Discover" },
  { to: "/for-you", label: "For You" },
  { to: "/favorites", label: "Favorites" },
  { to: "/ratings", label: "My Ratings" },
  { to: "/onboarding", label: "Onboarding" },
  { to: "/insights", label: "Insights" },
  { to: "/about", label: "About" },
];

export function Layout() {
  const { userId, setUserId } = useUser();
  const ready = useReady();
  const status = ready.data?.status;
  const statusColor =
    status === "ok"
      ? "text-emerald-400"
      : status === "degraded"
      ? "text-amber-400"
      : "text-slate-400";
  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-800 bg-bg/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-3 px-4 py-3">
          <Link to="/" className="mr-4 text-lg font-bold tracking-tight">
            <span className="text-accent">Movie</span>Rec
          </Link>
          <nav className="flex flex-1 flex-wrap gap-3 text-sm">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  "link " + (isActive ? "!text-white underline underline-offset-4" : "")
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2 text-xs">
            <span className={`hidden md:inline ${statusColor}`}>
              {status ?? "…"}
            </span>
            <label className="muted">User</label>
            <input
              type="number"
              min={1}
              max={943}
              value={userId}
              onChange={(e) => setUserId(Number(e.target.value))}
              className="input !w-20 !py-1 text-xs"
              aria-label="Demo user id"
            />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>
      <footer className="mt-8 border-t border-slate-800 py-6 text-center text-xs muted">
        Built for an ML internship portfolio. Recommendations use real MovieLens
        data; explanations are only shown when the underlying signal is present.
      </footer>
    </div>
  );
}
