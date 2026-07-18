import { act, createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import { dashboardKeys, useDashboardWidgetQuery, useFocusMode, useResetDashboardWidgets, useUpdateDashboardWidgets, useUpdateFocusMode } from "./useDashboardQueries";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, listDashboardWidgets: vi.fn(), getFocusMode: vi.fn(), saveDashboardWidgets: vi.fn(), resetDashboardWidgets: vi.fn(), updateFocusMode: vi.fn() };
});

const widgets = [{ id: "widget-1", widget_id: "quick_actions", display_name: "Quick Actions", enabled: true, sort_order: 0, size: "medium", created_at: "2026-01-01", updated_at: "2026-01-01" }] as never;
const focusMode = { id: "focus-1", active_mode: "Audition Mode", created_at: "2026-01-01", updated_at: "2026-01-01" } as never;

describe("Dashboard queries", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses deterministic resource keys", () => {
    expect(dashboardKeys.widgets).toEqual(queryKeys.dashboard.list({ resource: "widgets" }));
    expect(dashboardKeys.focusMode).toEqual(queryKeys.dashboard.list({ resource: "focusMode" }));
  });

  it("loads widgets and preserves widget API errors", async () => {
    vi.mocked(api.listDashboardWidgets).mockResolvedValueOnce(widgets);
    const loaded = renderHook(() => useDashboardWidgetQuery(), { wrapper: createTestQueryWrapper() });
    expect(loaded.result.current.isLoading).toBe(true);
    await waitFor(() => expect(loaded.result.current.data).toEqual(widgets));

    vi.mocked(api.listDashboardWidgets).mockRejectedValueOnce(new Error("widgets unavailable"));
    const failed = renderHook(() => useDashboardWidgetQuery(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(failed.result.current.isError).toBe(true));
    expect(failed.result.current.error?.message).toContain("widgets unavailable");
  });

  it("loads focus mode and preserves focus API errors", async () => {
    vi.mocked(api.getFocusMode).mockResolvedValueOnce(focusMode);
    const loaded = renderHook(() => useFocusMode(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(loaded.result.current.data).toEqual(focusMode));
    vi.mocked(api.getFocusMode).mockRejectedValueOnce(new Error("focus unavailable"));
    const failed = renderHook(() => useFocusMode(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(failed.result.current.isError).toBe(true));
  });

  it("does not refetch fresh configuration data after an immediate remount", async () => {
    vi.mocked(api.listDashboardWidgets).mockResolvedValue(widgets);
    const client = createTestQueryClient();
    const wrapper = createTestQueryWrapper(client);
    const first = renderHook(() => useDashboardWidgetQuery(), { wrapper });
    await waitFor(() => expect(first.result.current.data).toEqual(widgets));
    first.unmount();
    const second = renderHook(() => useDashboardWidgetQuery(), { wrapper });
    await waitFor(() => expect(second.result.current.data).toEqual(widgets));
    expect(api.listDashboardWidgets).toHaveBeenCalledTimes(1);
  });

  it("refetches configuration data after its stale window", async () => {
    vi.mocked(api.listDashboardWidgets).mockResolvedValue(widgets);
    const client = createTestQueryClient();
    client.setQueryData(dashboardKeys.widgets, widgets, { updatedAt: Date.now() - queryStaleTimes.configuration - 1 });
    renderHook(() => useDashboardWidgetQuery(), { wrapper: createTestQueryWrapper(client) });
    await waitFor(() => expect(api.listDashboardWidgets).toHaveBeenCalledTimes(1));
  });

  it("invalidates only widgets after save", async () => {
    vi.mocked(api.saveDashboardWidgets).mockResolvedValue(widgets);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateDashboardWidgets(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync(widgets));
    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: dashboardKeys.widgets });
  });

  it("invalidates only widgets after reset", async () => {
    vi.mocked(api.resetDashboardWidgets).mockResolvedValue(widgets);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useResetDashboardWidgets(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync());
    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: dashboardKeys.widgets });
  });

  it("invalidates only focus mode after update", async () => {
    vi.mocked(api.updateFocusMode).mockResolvedValue(focusMode);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateFocusMode(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync("Audition Mode"));
    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: dashboardKeys.focusMode });
  });

  it("preserves focus-mode mutation failures", async () => {
    vi.mocked(api.updateFocusMode).mockRejectedValue(new Error("focus save failed"));
    const { result } = renderHook(() => useUpdateFocusMode(), { wrapper: createTestQueryWrapper() });
    await act(() => result.current.mutateAsync("Analytics Mode").catch(() => undefined));
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toContain("focus save failed");
  });
});
