import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Reset the DOM between tests.
afterEach(() => {
  cleanup();
});

// Silence "not implemented" noise from jsdom for canvas (used by recharts).
// If any test renders recharts we simply assert the table view instead.
if (typeof (globalThis as unknown as { HTMLCanvasElement?: unknown }).HTMLCanvasElement !== "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).HTMLCanvasElement.prototype.getContext = () => null;
}
