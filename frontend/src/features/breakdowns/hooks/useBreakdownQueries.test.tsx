import { act, createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { invalidationContracts, keysForContract } from "../../../services/api/invalidationContracts";
import {
  breakdownKeys, selectOpportunityOptions, useApproveBreakdown, useAuditionReadiness, useBreakdownRecommendations,
  useBreakdowns, useCreateBreakdown, useDeepParseBreakdown, useDeleteBreakdown, useDiscoveryPlugins,
  useGenerateBreakdownStrategy, useHiddenBreakdowns, useMaterialMatches, useParseBreakdownText, useRecommendationFeedback,
  useRefreshDemographicCheck, useRejectBreakdown, useRunBreakdownDiscovery, useSubmissionQueue, useUpdateBreakdown, useExecuteQueueItem
} from "./useBreakdownQueries";

vi.mock("../api", () => ({
  listBreakdowns: vi.fn(async () => []), listHiddenBreakdowns: vi.fn(async () => []), listBreakdownRecommendations: vi.fn(async () => []),
  listDiscoveryPlugins: vi.fn(async () => []), listSubmissionQueue: vi.fn(async () => []), listAuditionReadiness: vi.fn(async () => []),
  listMaterialMatches: vi.fn(async () => []), getDiscoveryReport: vi.fn(async () => ({ candidates: [], top_rejection_reasons: {} })),
  createBreakdown: vi.fn(async () => ({})), updateBreakdown: vi.fn(async () => ({})), deleteBreakdown: vi.fn(async () => ({})),
  approveActingBreakdown: vi.fn(async () => ({})), rejectBreakdown: vi.fn(async () => ({})), deepParseBreakdown: vi.fn(async () => ({})),
  parseBreakdownText: vi.fn(async () => ({})), refreshDemographicCheck: vi.fn(async () => ({})), generateBreakdownStrategy: vi.fn(async () => ({})),
  sendRecommendationFeedback: vi.fn(async () => ({})), runBreakdownDiscovery: vi.fn(async () => ({})), queueSubmissionFromRecommendation: vi.fn(async () => ({})),
  approveSubmissionQueueItem: vi.fn(async () => ({})), rejectSubmissionQueueItem: vi.fn(async () => ({})), executeSubmissionQueueItem: vi.fn(async () => ({}))
}));

describe("Breakdowns Query ownership", () => {
  it("uses deterministic resource keys and one visible-opportunity cache", () => {
    expect(breakdownKeys.opportunities).toEqual(["breakdowns", "list", { resource: "opportunities" }]);
    expect(new Set(Object.values(breakdownKeys).map((key) => JSON.stringify(key))).size).toBe(Object.keys(breakdownKeys).length);
    expect(selectOpportunityOptions([{ id: "o1", project: "Pilot", role: "Doctor", project_type: "TV", status: "New" } as never]))
      .toEqual([{ id: "o1", project: "Pilot", role: "Doctor", project_type: "TV", status: "New" }]);
  });

  it.each([
    ["visible", useBreakdowns, api.listBreakdowns], ["hidden", useHiddenBreakdowns, api.listHiddenBreakdowns],
    ["recommendations", useBreakdownRecommendations, api.listBreakdownRecommendations], ["plugins", useDiscoveryPlugins, api.listDiscoveryPlugins],
    ["queue", useSubmissionQueue, api.listSubmissionQueue], ["readiness", useAuditionReadiness, api.listAuditionReadiness],
    ["matches", useMaterialMatches, api.listMaterialMatches]
  ])("loads %s through the Breakdowns API", async (_label, hook, request) => {
    const { result } = renderHook(() => hook(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(request).toHaveBeenCalled();
  });

  it.each([
    [useCreateBreakdown, { title: "Manual" }, api.createBreakdown],
    [useUpdateBreakdown, { id: "o1", patch: { role: "Doctor" } }, api.updateBreakdown],
    [useDeleteBreakdown, "o1", api.deleteBreakdown], [useApproveBreakdown, "o1", api.approveActingBreakdown],
    [useRejectBreakdown, { id: "o1", payload: { rejection_reason: "Not eligible" } }, api.rejectBreakdown],
    [useDeepParseBreakdown, "o1", api.deepParseBreakdown], [useParseBreakdownText, { id: "o1", text: "actual" }, api.parseBreakdownText],
    [useRefreshDemographicCheck, "o1", api.refreshDemographicCheck],
    [useRecommendationFeedback, { id: "r1", payload: { feedback_type: "Helpful" } }, api.sendRecommendationFeedback]
  ])("routes a mutation through its API and focused invalidation", async (hook, variables, request) => {
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => hook(), { wrapper: createTestQueryWrapper(client) });
    await act(async () => { await result.current.mutateAsync(variables as never); });
    expect(request).toHaveBeenCalled();
    expect(invalidate).toHaveBeenCalled();
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: ["breakdowns"] });
  });

  it("invalidates Breakdowns and public Source Library lists after discovery", async () => {
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useRunBreakdownDiscovery(), { wrapper: createTestQueryWrapper(client) });
    await act(async () => { await result.current.mutateAsync({ mode: "FilmTV", searchModes: ["Match My Profile"] }); });
    const keys = invalidate.mock.calls.map(([filters]) => JSON.stringify(filters?.queryKey));
    expect(keys).toContain(JSON.stringify(["sourceLibrary", "list", { resource: "sources" }]));
    expect(keys).toContain(JSON.stringify(breakdownKeys.discoveryReport));
  });

  it("invalidates only the queue after queue execution while Auditions remains transitional", async () => {
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useExecuteQueueItem(), { wrapper: createTestQueryWrapper(client) });
    await act(async () => { await result.current.mutateAsync("queue-1"); });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: breakdownKeys.queue });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: queryKeysForTest("auditions") });
  });

  it.each([
    ["create", useCreateBreakdown, { role: "Doctor" }, invalidationContracts.opportunityCreate],
    ["update", useUpdateBreakdown, { id: "o1", patch: { audition_deadline: "2026-08-01" } }, invalidationContracts.opportunityUpdate],
    ["manual parse", useParseBreakdownText, { id: "o1", text: "Self-tape due August 1" }, invalidationContracts.opportunityManualParse],
    ["deep parse", useDeepParseBreakdown, "o1", invalidationContracts.opportunityDeepParse],
    ["reject/archive", useRejectBreakdown, { id: "o1", payload: { rejection_reason: "Not eligible" } }, invalidationContracts.opportunityReject],
    ["strategy generation", useGenerateBreakdownStrategy, "o1", invalidationContracts.opportunityStrategyGenerate],
    ["recommendation feedback", useRecommendationFeedback, { id: "r1", payload: { feedback_type: "This Fits Me" } }, invalidationContracts.recommendationFeedbackCreate],
    ["hard delete", useDeleteBreakdown, "o1", invalidationContracts.opportunityDelete]
  ])("uses the typed %s invalidation contract without broad invalidation", async (_label, hook, variables, contract) => {
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => hook(), { wrapper: createTestQueryWrapper(client) });
    await act(async () => { await result.current.mutateAsync(variables as never); });
    const calls = invalidate.mock.calls.map(([filters]) => JSON.stringify(filters?.queryKey));
    expect(calls).toEqual(keysForContract(contract).map((key) => JSON.stringify(key)));
    expect(calls).not.toContain(JSON.stringify(["breakdowns"]));
    expect(calls).not.toContain(JSON.stringify(["dashboard"]));
    expect(calls).not.toContain(JSON.stringify(["system", "capabilities"]));
  });

  it("does not invalidate any cache after a create failure", async () => {
    vi.mocked(api.createBreakdown).mockRejectedValueOnce(new Error("create failed"));
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useCreateBreakdown(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync({ role: "Doctor" } as never)).rejects.toThrow("create failed");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("does not invalidate any cache after a protected delete failure", async () => {
    vi.mocked(api.deleteBreakdown).mockRejectedValueOnce(new Error("linked submissions"));
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDeleteBreakdown(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync("o-linked")).rejects.toThrow("linked submissions");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("does not invalidate any cache after strategy generation fails", async () => {
    vi.mocked(api.generateBreakdownStrategy).mockRejectedValueOnce(new Error("strategy failed"));
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useGenerateBreakdownStrategy(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync("o1")).rejects.toThrow("strategy failed");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("does not invalidate any cache after deep parse fails", async () => {
    vi.mocked(api.deepParseBreakdown).mockRejectedValueOnce(new Error("deep parse failed"));
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDeepParseBreakdown(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync("o1")).rejects.toThrow("deep parse failed");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("does not invalidate any cache after reject/archive fails", async () => {
    vi.mocked(api.rejectBreakdown).mockRejectedValueOnce(new Error("reject failed"));
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useRejectBreakdown(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync({ id: "o1", payload: { rejection_reason: "Not eligible" } })).rejects.toThrow("reject failed");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("keeps reject/archive success successful when background invalidation rejects", async () => {
    const client = createTestQueryClient();
    vi.spyOn(client, "invalidateQueries").mockRejectedValue(new Error("background owner unavailable"));
    const { result } = renderHook(() => useRejectBreakdown(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync({ id: "o1", payload: { rejection_reason: "Not eligible" } })).resolves.toEqual({});
  });

  it("keeps deep-parse success successful when background invalidation rejects", async () => {
    const client = createTestQueryClient();
    vi.spyOn(client, "invalidateQueries").mockRejectedValue(new Error("background owner unavailable"));
    const { result } = renderHook(() => useDeepParseBreakdown(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync("o1")).resolves.toEqual({});
  });

  it("does not invalidate any cache after recommendation feedback fails", async () => {
    vi.mocked(api.sendRecommendationFeedback).mockRejectedValueOnce(new Error("feedback failed"));
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useRecommendationFeedback(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync({ id: "r1", payload: { feedback_type: "This Fits Me" } })).rejects.toThrow("feedback failed");
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("keeps recommendation feedback successful when command-center refetch rejects", async () => {
    const client = createTestQueryClient();
    vi.spyOn(client, "invalidateQueries").mockRejectedValue(new Error("command center unavailable"));
    const { result } = renderHook(() => useRecommendationFeedback(), { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync({ id: "r1", payload: { feedback_type: "This Fits Me" } })).resolves.toEqual({});
  });
});

const queryKeysForTest = (feature: string) => [feature];
