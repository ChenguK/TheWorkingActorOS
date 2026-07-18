import { act, createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryKeys } from "../../../services/api/queryKeys";
import { createJournalEntry, deleteJournalEntry, listJournalEntries } from "../api";
import type { JournalCreatePayload } from "../types";
import { useCreateJournalEntry, useDeleteJournalEntry, useJournalEntries } from "./useJournalEntries";

vi.mock("../api", () => ({
  createJournalEntry: vi.fn(),
  deleteJournalEntry: vi.fn(),
  listJournalEntries: vi.fn(),
  updateJournalEntryNotes: vi.fn()
}));

const payload: JournalCreatePayload = {
  date: "2026-07-16",
  event_type: "Manual",
  title: "Journal entry",
  description: null,
  linked_breakdown_id: null,
  linked_audition_id: null,
  linked_material_id: null,
  linked_career_task_id: null,
  notes: null
};

describe("Journal query mutations", () => {
  beforeEach(() => vi.clearAllMocks());

  it("invalidates only the Journal list key after create", async () => {
    vi.mocked(createJournalEntry).mockResolvedValue({
      id: "journal-1",
      ...payload,
      created_at: "2026-07-16T12:00:00Z",
      updated_at: "2026-07-16T12:00:00Z"
    });
    const queryClient = createTestQueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useCreateJournalEntry(), {
      wrapper: createTestQueryWrapper(queryClient)
    });

    await act(async () => result.current.mutateAsync(payload));

    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.journal.lists() });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: [] });
  });

  it("keeps Journal caches isolated", () => {
    const first = createTestQueryClient();
    const second = createTestQueryClient();
    first.setQueryData(queryKeys.journal.list(), [{ id: "journal-1" }]);

    expect(second.getQueryData(queryKeys.journal.list())).toBeUndefined();
  });

  it("routes supported deletes through the Journal API and list invalidation", async () => {
    vi.mocked(deleteJournalEntry).mockResolvedValue(undefined);
    const queryClient = createTestQueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useDeleteJournalEntry(), {
      wrapper: createTestQueryWrapper(queryClient)
    });

    await act(async () => result.current.mutateAsync("journal-1"));

    expect(deleteJournalEntry).toHaveBeenCalledWith("journal-1");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: queryKeys.journal.lists() });
  });

  it("keeps fresh generated Journal history without a remount request", () => {
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(queryKeys.journal.list(), []);
    renderHook(() => useJournalEntries(), { wrapper: createTestQueryWrapper(queryClient) });
    expect(listJournalEntries).not.toHaveBeenCalled();
  });

  it("refetches Journal history after its workflow stale window", async () => {
    vi.mocked(listJournalEntries).mockResolvedValue([]);
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(queryKeys.journal.list(), [], { updatedAt: Date.now() - 61_000 });
    renderHook(() => useJournalEntries(), { wrapper: createTestQueryWrapper(queryClient) });
    await waitFor(() => expect(listJournalEntries).toHaveBeenCalledOnce());
  });
});
