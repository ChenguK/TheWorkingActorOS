import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";
import { clearTestQueryClients } from "./testUtils";

afterEach(() => {
  cleanup();
  clearTestQueryClients();
  vi.restoreAllMocks();
});

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
});

Object.defineProperty(window, "scrollTo", {
  writable: true,
  value: vi.fn()
});

Object.defineProperty(Element.prototype, "scrollIntoView", {
  writable: true,
  value: vi.fn()
});

Object.defineProperty(window, "requestAnimationFrame", {
  writable: true,
  value: (callback: FrameRequestCallback) => window.setTimeout(() => callback(Date.now()), 0)
});

Object.defineProperty(window, "cancelAnimationFrame", {
  writable: true,
  value: (id: number) => window.clearTimeout(id)
});

vi.stubGlobal(
  "fetch",
  vi.fn(() => Promise.reject(new Error("Unexpected fetch call in a frontend test. Mock the feature API module instead.")))
);
