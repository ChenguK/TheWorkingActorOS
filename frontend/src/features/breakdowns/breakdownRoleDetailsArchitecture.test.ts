import { describe, expect, it } from "vitest";

const modules = import.meta.glob<string>(
  ["./components/*.{ts,tsx}", "./index.ts"],
  { eager: true, import: "default", query: "?raw" }
);

describe("BreakdownRoleDetails route-private boundary", () => {
  it("keeps the exact presentation-only contract", () => {
    const roleDetails = modules["./components/BreakdownRoleDetails.tsx"];
    expect(roleDetails).toContain('export function RoleViewer({ roles }: { roles: Opportunity["breakdown_roles"] })');
    expect(roleDetails).not.toMatch(/useState|useEffect|useMutation|useQuery|useQueryClient/);
    expect(roleDetails).not.toMatch(/services\/api|queryKey|QueryClient|\bfetch\s*\(|\bapi\./);
    expect(roleDetails).not.toMatch(/on[A-Z][A-Za-z]+\s*:/);
  });

  it("is private, acyclic, and imported directly by its two production consumers", () => {
    const publicBarrel = modules["./index.ts"];
    const details = modules["./components/BreakdownDetails.tsx"];
    const manager = modules["./components/BreakdownManager.tsx"];
    const viewer = modules["./components/BreakdownViewer.tsx"];
    expect(publicBarrel).not.toContain("BreakdownRoleDetails");
    expect(publicBarrel).not.toContain("RoleViewer");
    expect(details).not.toContain("BreakdownRoleDetails");
    expect(details).not.toContain("export function RoleViewer");
    expect(manager).toContain('from "./BreakdownRoleDetails"');
    expect(viewer).toContain('from "./BreakdownRoleDetails"');
  });
});
