import { createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryKeys } from "../../../services/api/queryKeys";
import * as api from "../api";
import { materialsListKey, useMaterialOptions, useMaterials } from "./useMaterials";

vi.mock("../api", () => ({
  analyzeMaterial: vi.fn(), deleteMaterial: vi.fn(), listMaterials: vi.fn(), updateMaterial: vi.fn(), uploadMaterial: vi.fn()
}));

describe("Materials query keys", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses one deterministic list cache for all material-type selectors", () => {
    expect(materialsListKey).toEqual(queryKeys.materials.list());
    expect(queryKeys.materials.list({ assetType: "Headshot" })).not.toEqual(materialsListKey);
  });

  it("deduplicates simultaneous public consumers of the material list", async () => {
    let resolve!: (value: never) => void;
    vi.mocked(api.listMaterials).mockReturnValue(new Promise((done) => { resolve = done; }));
    const client = createTestQueryClient();
    const wrapper = createTestQueryWrapper(client);
    const list = renderHook(() => useMaterials(), { wrapper });
    const options = renderHook(() => useMaterialOptions(), { wrapper });
    expect(api.listMaterials).toHaveBeenCalledTimes(1);
    resolve([] as never);
    await waitFor(() => expect(list.result.current.data).toEqual([]));
    await waitFor(() => expect(options.result.current.data).toEqual([]));
  });
});
