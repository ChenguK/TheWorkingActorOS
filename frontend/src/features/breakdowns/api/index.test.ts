import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../../../services/api";
import {
  approveSubmissionQueueItem,
  executeSubmissionQueueItem,
  queueSubmissionFromRecommendation,
  rejectSubmissionQueueItem,
  runBreakdownDiscovery
} from "./index";

vi.mock("../../../services/api", () => ({
  api: { get: vi.fn(), post: vi.fn() }
}));

describe("Breakdowns feature API", () => {
  beforeEach(() => vi.clearAllMocks());

  it("builds a typed discovery request from mode and matching intent", async () => {
    vi.mocked(api.post).mockResolvedValue({});
    await runBreakdownDiscovery({
      mode: "FilmTV",
      searchModes: ["Match My Profile", "Find Stretch Roles"],
      specificArchetype: "Attorney"
    });

    expect(api.post).toHaveBeenCalledWith(
      "/automation/discovery/run?mode=FilmTV&search_modes=Match+My+Profile&search_modes=Find+Stretch+Roles&specific_archetype=Attorney"
    );
  });

  it("routes Theater discovery through the same typed feature API", async () => {
    vi.mocked(api.post).mockResolvedValue({});
    await runBreakdownDiscovery({
      mode: "Theater",
      searchModes: ["Match My Archetypes"]
    });

    expect(api.post).toHaveBeenCalledWith(
      "/automation/discovery/run?mode=Theater&search_modes=Match+My+Archetypes"
    );
  });

  it("owns all submission queue endpoint calls", async () => {
    vi.mocked(api.post).mockResolvedValue(undefined);
    await queueSubmissionFromRecommendation("recommendation-1");
    await approveSubmissionQueueItem("queue-1");
    await rejectSubmissionQueueItem("queue-2");
    await executeSubmissionQueueItem("queue-3");

    expect(api.post).toHaveBeenNthCalledWith(1, "/automation/submission-queue/from-recommendation/recommendation-1");
    expect(api.post).toHaveBeenNthCalledWith(2, "/automation/submission-queue/queue-1/approve");
    expect(api.post).toHaveBeenNthCalledWith(3, "/automation/submission-queue/queue-2/reject");
    expect(api.post).toHaveBeenNthCalledWith(4, "/automation/submission-queue/queue-3/execute");
  });
});
