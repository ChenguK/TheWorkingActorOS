import { describe, expect, it } from "vitest";
import type { Asset } from "../../../types/domain";
import { materialsListKey, selectMaterialOptions } from "./useMaterials";
import { queryKeys } from "../../../services/api/queryKeys";

describe("public Material options", () => {
  it("preserves compact identity, type, and archetype metadata on the authoritative list key", () => {
    const asset = { id: "asset-1", asset_name: "Attorney Headshot", asset_type: "Headshot", archetype_names: ["Attorney"], description: "Full record" } as Asset;
    expect(selectMaterialOptions([asset])).toEqual([{ id: "asset-1", asset_name: "Attorney Headshot", asset_type: "Headshot", archetype_names: ["Attorney"] }]);
    expect(materialsListKey).toEqual(queryKeys.materials.list());
  });
});
