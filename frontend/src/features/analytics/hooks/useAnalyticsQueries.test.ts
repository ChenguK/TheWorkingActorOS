import { describe, expect, it, vi } from "vitest";
import { queryKeys } from "../../../services/api/queryKeys";
import { createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { getIntelligenceDashboard, getMaterialPerformance } from "../api";
import { analyticsKeys, useIntelligenceDashboard, useMaterialPerformance } from "./useAnalyticsQueries";
import { calculateCallbackBookingMetrics } from "../utils";

vi.mock("../api", () => ({
  getCastingPatterns: vi.fn(), getIntelligenceDashboard: vi.fn(), getMaterialPerformance: vi.fn(), getOperationsDashboard: vi.fn()
}));

describe("Analytics query keys", () => {
  it("uses deterministic, distinct endpoint caches", () => {
    expect(analyticsKeys.operations).toEqual(queryKeys.analytics.list({ resource: "operationsDashboard" }));
    expect(analyticsKeys.intelligence).toEqual(queryKeys.analytics.list({ resource: "intelligenceDashboard" }));
    expect(analyticsKeys.industryTrends).toEqual(queryKeys.analytics.list({ resource: "industryTrends" }));
    expect(analyticsKeys.materialPerformance).toEqual(queryKeys.analytics.list({ resource: "materialPerformance" }));
    expect(new Set(Object.values(analyticsKeys).map((key) => JSON.stringify(key))).size).toBe(4);
  });

  it("preserves the transitional raw submission metric contract", () => {
    const metrics = calculateCallbackBookingMetrics([
      { current_status: "Submitted" },
      { current_status: "Self-Tape Callback" },
      { current_status: "Booked" }
    ] as never);
    expect(metrics).toEqual({ submissions: 3, callbacks: 2, bookings: 1, callbackRate: 2 / 3, bookingRate: 1 / 3 });
  });

  it.each([
    ["intelligence", analyticsKeys.intelligence, useIntelligenceDashboard, getIntelligenceDashboard, {}],
    ["material performance", analyticsKeys.materialPerformance, useMaterialPerformance, getMaterialPerformance, []]
  ] as const)("keeps fresh %s aggregates without a remount request", (_label, key, hook, request, cached) => {
    const client = createTestQueryClient();
    client.setQueryData(key, cached);
    renderHook(() => hook(), { wrapper: createTestQueryWrapper(client) });
    expect(request).not.toHaveBeenCalled();
  });

  it.each([
    [analyticsKeys.intelligence, useIntelligenceDashboard, getIntelligenceDashboard, {}],
    [analyticsKeys.materialPerformance, useMaterialPerformance, getMaterialPerformance, []]
  ] as const)("refetches a stale derived aggregate after its workflow window", async (key, hook, request, response) => {
    vi.mocked(request).mockResolvedValue(response as never);
    const client = createTestQueryClient();
    client.setQueryData(key, response, { updatedAt: Date.now() - 61_000 });
    renderHook(() => hook(), { wrapper: createTestQueryWrapper(client) });
    await waitFor(() => expect(request).toHaveBeenCalledOnce());
  });
});
