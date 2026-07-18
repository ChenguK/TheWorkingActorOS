import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createTestQueryClient, createTestQueryWrapper } from "../../../test/testUtils";
import { materialsListKey } from "./useMaterials";
import { auditionKeys } from "../../auditions";
import {
  reusableSelfTapeKeys,
  useCreateReusableSelfTape,
  useDeleteReusableSelfTape,
  useReusableSelfTapeAnalytics,
  useReusableSelfTapes,
  useUpdateReusableSelfTape
} from "./useReusableSelfTapes";
import * as materialsApi from "../api";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return {
    ...actual,
    listReusableSelfTapes: vi.fn(),
    getReusableSelfTapeAnalytics: vi.fn(),
    createSelfTape: vi.fn(),
    updateSelfTape: vi.fn(),
    deleteSelfTape: vi.fn()
  };
});

const tape = {
  id: "tape-1", title: "Authority", role_type: "Doctor", archetypes: ["Authority"],
  file_path: "/media/authority.mp4", linked_opportunity_id: null, linked_submission_id: null,
  outcome: "Callback", notes: "Strong take", date_created: "2026-07-01",
  created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z"
};

describe("reusable Materials self-tape queries", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses deterministic keys that cannot collide with assets or Auditions workflow self-tapes", () => {
    expect(reusableSelfTapeKeys.library).toEqual(["materials", "list", { resource: "reusableSelfTapes" }]);
    expect(reusableSelfTapeKeys.analytics).toEqual(["materials", "list", { resource: "reusableSelfTapeAnalytics" }]);
    expect(reusableSelfTapeKeys.library).not.toEqual(materialsListKey);
    expect(reusableSelfTapeKeys.library).not.toEqual(auditionKeys.selfTapes);
  });

  it("loads the reusable library and analytics through the Materials API", async () => {
    vi.mocked(materialsApi.listReusableSelfTapes).mockResolvedValue([tape]);
    vi.mocked(materialsApi.getReusableSelfTapeAnalytics).mockResolvedValue({ by_archetype: [], by_outcome: [], best_performing_tapes: [tape], underused_tapes: [] });
    const wrapper = createTestQueryWrapper();
    const library = renderHook(() => useReusableSelfTapes(), { wrapper });
    const analytics = renderHook(() => useReusableSelfTapeAnalytics(), { wrapper });
    await waitFor(() => expect(library.result.current.data).toEqual([tape]));
    await waitFor(() => expect(analytics.result.current.data?.best_performing_tapes).toEqual([tape]));
  });

  it.each([
    ["create", useCreateReusableSelfTape, materialsApi.createSelfTape, tape],
    ["update", useUpdateReusableSelfTape, materialsApi.updateSelfTape, { id: tape.id, patch: { notes: "Updated" } }],
    ["delete", useDeleteReusableSelfTape, materialsApi.deleteSelfTape, tape.id]
  ] as const)("invalidates only reusable caches after %s", async (_name, useMutationHook, apiMethod, variables) => {
    vi.mocked(apiMethod as ReturnType<typeof vi.fn>).mockResolvedValue(tape);
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries").mockResolvedValue();
    const { result } = renderHook(() => useMutationHook() as ReturnType<typeof useCreateReusableSelfTape>, { wrapper: createTestQueryWrapper(client) });
    await act(async () => { await result.current.mutateAsync(variables as never); });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: reusableSelfTapeKeys.library });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: reusableSelfTapeKeys.analytics });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: materialsListKey });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: auditionKeys.selfTapes });
  });

  it.each([
    [useCreateReusableSelfTape, tape],
    [useUpdateReusableSelfTape, { id: tape.id, patch: { notes: "Updated" } }],
    [useDeleteReusableSelfTape, tape.id]
  ] as const)("does not invalidate when a reusable mutation fails", async (useMutationHook, variables) => {
    const failure = new Error("save failed");
    vi.mocked(materialsApi.createSelfTape).mockRejectedValue(failure);
    vi.mocked(materialsApi.updateSelfTape).mockRejectedValue(failure);
    vi.mocked(materialsApi.deleteSelfTape).mockRejectedValue(failure);
    const client = createTestQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useMutationHook() as ReturnType<typeof useCreateReusableSelfTape>, { wrapper: createTestQueryWrapper(client) });
    await expect(result.current.mutateAsync(variables as never)).rejects.toThrow("save failed");
    expect(invalidate).not.toHaveBeenCalled();
  });
});
