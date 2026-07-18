import { act, createTestQueryClient, createTestQueryWrapper, renderHook } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  auditionKeys, useCreateAuditionPerformanceNote, useCreateCallbackEvent, useCreateSubmission,
  useDeleteSubmission, useUpdateSubmission, useUpdateSubmissionStatus, useUpdateWorkflowSelfTape
} from "./useAuditionQueries";
import * as api from "../api";
import { publicInvalidationKeys } from "../../../services/api/invalidationContracts";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual, recordSubmission: vi.fn(), updateSubmission: vi.fn(), deleteSubmission: vi.fn(),
    addSubmissionStatus: vi.fn(), createCallbackEvent: vi.fn(), updateSelfTapeTask: vi.fn(), createAuditionNote: vi.fn()
  };
});

describe("Auditions query boundary", () => {
  beforeEach(() => vi.clearAllMocks());

  it("provides deterministic resource keys", () => {
    expect(auditionKeys.submissions).toEqual(["auditions", "list", { resource: "submissions" }]);
    expect(auditionKeys.selfTapes).toEqual(["auditions", "list", { resource: "selfTapes" }]);
    expect(auditionKeys.callbacks).toEqual(["auditions", "list", { resource: "callbacks" }]);
    expect(auditionKeys.performanceNotes).toEqual(["auditions", "list", { resource: "auditionJournal" }]);
  });

  it("invalidates submission creation's proven synchronous side effects", async () => {
    vi.mocked(api.recordSubmission).mockResolvedValue({ id: "submission-1" } as never);
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useCreateSubmission(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({}));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: auditionKeys.submissions });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.calendarEvents });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.journalEntries });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.analyticsOperations });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: ["dashboard"] });
  });

  it("invalidates the self-tape owner cache without a persisted Calendar-row invalidation", async () => {
    vi.mocked(api.updateSelfTapeTask).mockResolvedValue({ id: "tape-1" } as never);
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateWorkflowSelfTape(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({ id: "tape-1", patch: { tape_due_at: "2026-08-01" } }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: auditionKeys.selfTapes });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.commandCenter });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.calendarEvents });
  });

  it("invalidates callback side effects through owner caches, not Calendar rows", async () => {
    vi.mocked(api.createCallbackEvent).mockResolvedValue({ id: "callback-1" } as never);
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useCreateCallbackEvent(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({}));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: auditionKeys.callbacks });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.journalEntries });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.calendarEvents });
  });

  it("keeps a notes-only submission update out of unrelated Analytics caches", async () => {
    vi.mocked(api.updateSubmission).mockResolvedValue({ id: "submission-1" } as never);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateSubmission(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({ id: "submission-1", patch: { notes: "Private note" } }));
    expect(invalidate).toHaveBeenCalledTimes(1);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: auditionKeys.submissions });
  });

  it("invalidates material performance for linked-material changes", async () => {
    vi.mocked(api.updateSubmission).mockResolvedValue({ id: "submission-1" } as never);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateSubmission(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({ id: "submission-1", patch: { asset_ids: ["asset-1"] } }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.analyticsMaterialPerformance });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.analyticsOperations });
  });

  it("invalidates outcome aggregates and actor Journal only for meaningful statuses", async () => {
    vi.mocked(api.addSubmissionStatus).mockResolvedValue({ id: "submission-1" } as never);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useUpdateSubmissionStatus(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({ id: "submission-1", status: "Booked" }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.analyticsIntelligence });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.journalEntries });
  });

  it("invalidates deletion aggregates but retains historical Journal entries", async () => {
    vi.mocked(api.deleteSubmission).mockResolvedValue(undefined);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDeleteSubmission(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync("submission-1"));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.analyticsOperations });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.journalEntries });
  });

  it("keeps Auditions performance notes separate from actor Journal", async () => {
    vi.mocked(api.createAuditionNote).mockResolvedValue({ id: "note-1" } as never);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useCreateAuditionPerformanceNote(), { wrapper: createTestQueryWrapper(client) });
    await act(() => result.current.mutateAsync({}));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: auditionKeys.performanceNotes });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: publicInvalidationKeys.journalEntries });
  });
});
