import { act, createTestQueryClient, createTestQueryWrapper, renderHook } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryKeys } from "../../../services/api/queryKeys";
import { createSource, rejectSource, restoreSource } from "../api";
import {
  sourceArchiveKey,
  sourceListKey,
  useCreateSourceResearchItem,
  useRejectSourceResearchItem,
  useRestoreSourceResearchItem
} from "./useSourceLibrary";

vi.mock("../api", () => ({
  approveSource: vi.fn(), createSource: vi.fn(), findNewSources: vi.fn(), listArchivedSources: vi.fn(), listSources: vi.fn(),
  rejectSource: vi.fn(), restoreSource: vi.fn(), updateSource: vi.fn()
}));

describe("Source Library query boundaries", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses deterministic, distinct list and archive keys", () => {
    expect(sourceListKey).toEqual(queryKeys.sourceLibrary.list({ resource: "sources" }));
    expect(sourceArchiveKey).toEqual(queryKeys.sourceLibrary.list({ resource: "archive" }));
    expect(queryKeys.sourceLibrary.list({ status: "Researching" })).toEqual(queryKeys.sourceLibrary.list({ status: "Researching" }));
  });

  it("invalidates only Source Library list keys after create", async () => {
    vi.mocked(createSource).mockResolvedValue({ id: "source-1" } as never);
    const queryClient = createTestQueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const { result } = renderHook(() => useCreateSourceResearchItem(), { wrapper: createTestQueryWrapper(queryClient) });
    await act(async () => result.current.mutateAsync({ name: "Source" }));
    expect(invalidate).toHaveBeenCalledTimes(2);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: sourceListKey });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: sourceArchiveKey });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: [] });
  });

  it("invalidates ordinary and archive views after reject and restore", async () => {
    vi.mocked(rejectSource).mockResolvedValue({ id: "source-1" } as never);
    vi.mocked(restoreSource).mockResolvedValue({ id: "source-1" } as never);
    const queryClient = createTestQueryClient();
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const wrapper = createTestQueryWrapper(queryClient);
    const rejected = renderHook(() => useRejectSourceResearchItem(), { wrapper });
    const restored = renderHook(() => useRestoreSourceResearchItem(), { wrapper });
    await act(async () => rejected.result.current.mutateAsync({ sourceId: "source-1", reason: "Duplicate" }));
    await act(async () => restored.result.current.mutateAsync("source-1"));
    expect(rejectSource).toHaveBeenCalledWith("source-1", "Duplicate");
    expect(restoreSource).toHaveBeenCalledWith("source-1");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: sourceListKey });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: sourceArchiveKey });
  });
});
