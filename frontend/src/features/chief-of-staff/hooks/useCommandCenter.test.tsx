import { act, createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { commandCenterKey, useCommandCenter, usePlatformCheckIn, useRefreshCommandCenter, useResolveOutcomeNudge } from "./useCommandCenter";
import { executiveBriefKeys, useGenerateWeeklyBrief } from "./useExecutiveBriefs";
import { queryKeys } from "../../../services/api/queryKeys";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, getCommandCenter: vi.fn(), updatePlatformCheckIn: vi.fn(), resolveOutcomeNudge: vi.fn(), refreshCommandCenter: vi.fn(), generateWeeklyBrief: vi.fn() };
});

const snapshot = { today_opportunities: [], executive_priorities: [], queued_submissions: [], upcoming_deadlines: [], outcome_nudges: [], career_tasks: [], material_gaps: [], asset_performance: [] } as never;

describe("Chief of Staff command-center queries", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses deterministic, separate command-center and executive-brief keys", () => {
    expect(commandCenterKey).toEqual(queryKeys.chiefOfStaff.list({ resource: "commandCenter" }));
    expect(executiveBriefKeys.list).toEqual(queryKeys.chiefOfStaff.list({ resource: "briefs" }));
    expect(commandCenterKey).not.toEqual(executiveBriefKeys.list);
  });

  it("exposes loading and then command-center data", async () => {
    let resolve!: (value: never) => void;
    vi.mocked(api.getCommandCenter).mockReturnValue(new Promise((done) => { resolve = done; }));
    const { result } = renderHook(() => useCommandCenter(), { wrapper: createTestQueryWrapper() });
    expect(result.current.isLoading).toBe(true);
    resolve(snapshot);
    await waitFor(() => expect(result.current.data).toEqual(snapshot));
  });

  it("preserves command-center API errors", async () => {
    vi.mocked(api.getCommandCenter).mockRejectedValue(new Error("command center unavailable"));
    const { result } = renderHook(() => useCommandCenter(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toContain("command center unavailable");
  });

  it("refetches live command-center state after an immediate remount", async () => {
    vi.mocked(api.getCommandCenter).mockResolvedValue(snapshot);
    const client = createTestQueryClient();
    const wrapper = createTestQueryWrapper(client);
    const first = renderHook(() => useCommandCenter(), { wrapper });
    await waitFor(() => expect(first.result.current.data).toEqual(snapshot));
    first.unmount();
    const second = renderHook(() => useCommandCenter(), { wrapper });
    expect(second.result.current.data).toEqual(snapshot);
    await waitFor(() => expect(api.getCommandCenter).toHaveBeenCalledTimes(2));
    second.unmount();
  });

  it("focuses invalidation after platform check-in", async () => {
    vi.mocked(api.updatePlatformCheckIn).mockResolvedValue({} as never);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => usePlatformCheckIn(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({ subscriptionId: "sub-1", checkedToday: true }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: commandCenterKey });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["journal", "list"] });
  });

  it("focuses invalidation after outcome-nudge resolution", async () => {
    vi.mocked(api.resolveOutcomeNudge).mockResolvedValue({ status: "resolved" });
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useResolveOutcomeNudge(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync("nudge-1"));
    expect(invalidate).toHaveBeenCalledTimes(1); expect(invalidate).toHaveBeenCalledWith({ queryKey: commandCenterKey });
  });

  it("focuses invalidation after explicit command-center regeneration", async () => {
    vi.mocked(api.refreshCommandCenter).mockResolvedValue(snapshot);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useRefreshCommandCenter(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync());
    expect(invalidate).toHaveBeenCalledTimes(1); expect(invalidate).toHaveBeenCalledWith({ queryKey: commandCenterKey });
  });

  it("keeps brief generation invalidation on the separate executive-brief cache", async () => {
    vi.mocked(api.generateWeeklyBrief).mockResolvedValue({} as never);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useGenerateWeeklyBrief(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync());
    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: executiveBriefKeys.list });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: commandCenterKey });
  });
});
