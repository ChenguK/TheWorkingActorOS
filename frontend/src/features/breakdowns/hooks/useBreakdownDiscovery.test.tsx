import { act, createTestQueryWrapper, renderHook } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  approveSubmissionQueueItem,
  executeSubmissionQueueItem,
  queueSubmissionFromRecommendation,
  rejectSubmissionQueueItem,
  runBreakdownDiscovery
} from "../api";
import { useBreakdownDiscovery, useSubmissionQueueActions } from "./useBreakdownDiscovery";

vi.mock("../api", () => ({
  approveSubmissionQueueItem: vi.fn(),
  executeSubmissionQueueItem: vi.fn(),
  queueSubmissionFromRecommendation: vi.fn(),
  rejectSubmissionQueueItem: vi.fn(),
  runBreakdownDiscovery: vi.fn()
}));

const discoveryResult = {
  discovery_mode: "FilmTV" as const,
  search_modes: ["Match My Profile" as const],
  opportunities_created: 1,
  opportunities_hidden: 0,
  opportunities_rejected: 0,
  total_found: 1,
  total_rejected: 0,
  total_hidden: 0,
  total_visible: 1,
  limit_reached: false,
  rejection_reasons_summary: {},
  sources_run: 1,
  coverage: {
    approved_source_records: 1,
    approved_source_record_names: ["Example"],
    active_source_records: 1,
    operational_mode_sources_available: 1,
    operational_mode_source_names: ["Example"],
    sources_attempted: 1,
    source_names_attempted: ["Example"],
    successful_source_checks: 1,
    source_candidates_returned: 1,
    sources_returning_candidates: 1,
    approved_active_sources_checked: 1,
    approved_active_source_names_checked: ["Example"],
    eligible_sources_skipped: 0,
    skipped_source_reasons: [],
    approved_mode_sources_available: 1,
    approved_mode_sources_label: "Film/TV sources",
    suggested_sources_awaiting_approval: 0,
    coverage_level: "Limited",
    scope_note: "Approved sources only."
  }
};
const wrapper = createTestQueryWrapper();

describe("Breakdowns network hooks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("runs Film/TV discovery through the feature API", async () => {
    vi.mocked(runBreakdownDiscovery).mockResolvedValue(discoveryResult);
    const { result } = renderHook(() => useBreakdownDiscovery(), { wrapper });

    let response;
    await act(async () => {
      response = await result.current.run({ mode: "FilmTV", searchModes: ["Match My Profile"] });
    });

    expect(runBreakdownDiscovery).toHaveBeenCalledWith({ mode: "FilmTV", searchModes: ["Match My Profile"] });
    expect(response).toEqual(discoveryResult);
    expect(result.current.discovering).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("runs Theater discovery and exposes meaningful API errors", async () => {
    vi.mocked(runBreakdownDiscovery).mockRejectedValue(new Error("Discovery provider unavailable"));
    const { result } = renderHook(() => useBreakdownDiscovery(), { wrapper });

    await act(async () => {
      await result.current.run({ mode: "Theater", searchModes: ["Match My Archetypes"] });
    });

    expect(runBreakdownDiscovery).toHaveBeenCalledWith({ mode: "Theater", searchModes: ["Match My Archetypes"] });
    expect(result.current.error).toBe("Discovery provider unavailable");
  });

  it("routes submission queue actions through the feature API and refreshes", async () => {
    vi.mocked(queueSubmissionFromRecommendation).mockResolvedValue(undefined);
    vi.mocked(approveSubmissionQueueItem).mockResolvedValue(undefined);
    vi.mocked(rejectSubmissionQueueItem).mockResolvedValue(undefined);
    vi.mocked(executeSubmissionQueueItem).mockResolvedValue(undefined);
    const { result } = renderHook(() => useSubmissionQueueActions(), { wrapper });

    await act(async () => result.current.queueRecommendation("recommendation-1"));
    await act(async () => result.current.approve("queue-1"));
    await act(async () => result.current.reject("queue-2"));
    await act(async () => result.current.execute("queue-3"));

    expect(vi.mocked(queueSubmissionFromRecommendation).mock.calls[0]?.[0]).toBe("recommendation-1");
    expect(vi.mocked(approveSubmissionQueueItem).mock.calls[0]?.[0]).toBe("queue-1");
    expect(vi.mocked(rejectSubmissionQueueItem).mock.calls[0]?.[0]).toBe("queue-2");
    expect(vi.mocked(executeSubmissionQueueItem).mock.calls[0]?.[0]).toBe("queue-3");
  });
});
