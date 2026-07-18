import { describe, expect, it } from "vitest";

const production = import.meta.glob<string>(["../**/*.ts", "../**/*.tsx", "!../**/*.test.*", "!../**/*.spec.*", "!../test/**"], {
  eager: true,
  import: "default",
  query: "?raw"
});

describe("global server-state architecture retirement", () => {
  const source = Object.values(production).join("\n");

  it("does not restore the obsolete loader, universal route bag, or global mutation callback", () => {
    const obsoleteLoader = ["load", "Workflow", "Data"].join("");
    const obsoleteType = ["Workflow", "Page", "Data"].join("");
    const obsoleteCallback = ["on", "Changed"].join("");
    expect(source).not.toContain(obsoleteLoader);
    expect(source).not.toContain(obsoleteType);
    expect(source).not.toContain(obsoleteCallback);
  });

  it("keeps one infrastructure-owned production QueryClient and none in features", () => {
    const constructors = Object.entries(production).filter(([, text]) => /new QueryClient\s*\(/.test(text));
    expect(constructors.map(([path]) => path)).toEqual(["./queryClient.ts"]);
    expect(Object.entries(production).filter(([path, text]) => path.startsWith("../features/") && /new QueryClient\s*\(/.test(text))).toEqual([]);
  });

  it("does not replace the loader with broad root invalidation", () => {
    expect(source).not.toMatch(/invalidateQueries\s*\(\s*\)/);
    expect(source).not.toMatch(/invalidateQueries\s*\(\s*\{\s*(?:type:\s*["']all["']\s*)?\}\s*\)/);
  });

  it("keeps the old reusable self-tape loader endpoints out of the app shell", () => {
    const appShell = [production["../App.tsx"], production["../layout/TopNavigation.tsx"]].join("\n");
    expect(appShell).not.toContain("/intelligence/self-tapes");
    expect(appShell).not.toMatch(/api\.(get|post|put|patch|delete)/);
  });
});
