// Minimal fetch mock so smoke tests never touch the network.
// Each test sets its own route → response map via `mockOnce`.

type MockResponse = { status?: number; body?: unknown };
type Route = string;

const routes = new Map<Route, MockResponse>();

export function mockOnce(route: Route, body: unknown, status = 200) {
  routes.set(route, { status, body });
}

export function resetMocks() {
  routes.clear();
}

export const fetchMock = async (input: RequestInfo | URL, init?: RequestInit) => {
  const url = typeof input === "string" ? input : input.toString();
  const match = routes.get(url);
  if (!match) {
    return new Response(
      JSON.stringify({ detail: `unmocked ${init?.method ?? "GET"} ${url}` }),
      { status: 404, headers: { "content-type": "application/json" } },
    );
  }
  return new Response(JSON.stringify(match.body ?? null), {
    status: match.status ?? 200,
    headers: { "content-type": "application/json" },
  });
};

if (typeof globalThis !== "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).fetch = fetchMock;
}
