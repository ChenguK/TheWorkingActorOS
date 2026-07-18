import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { queryKeys } from "../../../services/api/queryKeys";
import { createTestQueryWrapper } from "../../../test/testUtils";
import { updateCommunicationLog } from "../api";
import {
  communicationLogsKey,
  relationshipAnalyticsKey,
  relationshipsListKey,
  useUpdateRelationshipInteraction
} from "./useRelationshipQueries";

vi.mock("../api", () => ({
  createCommunicationLog: vi.fn(), createRelationship: vi.fn(), deleteCommunicationLog: vi.fn(), deleteRelationship: vi.fn(),
  getRelationshipAnalytics: vi.fn(), listCommunicationLogs: vi.fn(), listRelationships: vi.fn(),
  updateCommunicationLog: vi.fn(), updateRelationship: vi.fn()
}));

describe("Relationships query boundaries", () => {
  it("creates deterministic, distinct resource and filtered keys", () => {
    expect(relationshipsListKey).toEqual(queryKeys.relationships.list({ resource: "relationships" }));
    expect(relationshipAnalyticsKey).toEqual(queryKeys.relationships.list({ resource: "analytics" }));
    expect(communicationLogsKey).toEqual(queryKeys.relationships.list({ resource: "communicationLogs" }));
    expect(queryKeys.relationships.list({ strength: "Strong", role: "Agent" })).toEqual(
      queryKeys.relationships.list({ strength: "Strong", role: "Agent" })
    );
  });

  it("supports the existing interaction update endpoint", async () => {
    vi.mocked(updateCommunicationLog).mockResolvedValue({
      id: "log-1", date: "2026-07-12", topic: "Updated", follow_up_needed: false,
      created_at: "2026-07-12T00:00:00Z", updated_at: "2026-07-12T00:00:00Z"
    });
    const { result } = renderHook(() => useUpdateRelationshipInteraction(), { wrapper: createTestQueryWrapper() });
    result.current.mutate({ logId: "log-1", patch: { topic: "Updated" } });
    await waitFor(() => expect(updateCommunicationLog).toHaveBeenCalledWith("log-1", { topic: "Updated" }));
  });
});
