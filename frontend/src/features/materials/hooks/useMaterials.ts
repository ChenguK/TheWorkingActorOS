import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { invalidateInBackground, publicInvalidationKeys } from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { Asset, AssetType } from "../../../types/domain";
import type { MaterialOption } from "../types";
import { analyzeMaterial, deleteMaterial, listMaterials, updateMaterial, uploadMaterial } from "../api";

export const materialsListKey = queryKeys.materials.list();

export function useMaterials() {
  return useQuery({
    queryKey: materialsListKey,
    queryFn: listMaterials,
    staleTime: queryStaleTimes.workflow
  });
}

export function useMaterialsByType(assetType: AssetType) {
  return useQuery({
    queryKey: materialsListKey,
    queryFn: listMaterials,
    staleTime: queryStaleTimes.workflow,
    select: (assets) => assets.filter((asset) => asset.asset_type === assetType)
  });
}

export function selectMaterialOptions(assets: Asset[]): MaterialOption[] {
  return assets.map(({ id, asset_name, asset_type, archetype_names }) => ({ id, asset_name, asset_type, archetype_names }));
}

export function useMaterialOptions() {
  return useQuery({ queryKey: materialsListKey, queryFn: listMaterials, staleTime: queryStaleTimes.workflow, select: selectMaterialOptions });
}

function useInvalidateMaterials() {
  const queryClient = useQueryClient();
  return (...derived: readonly (readonly unknown[])[]) => invalidateInBackground(queryClient, [materialsListKey, ...derived]);
}

export function useUploadMaterial() {
  const invalidate = useInvalidateMaterials();
  return useMutation({ mutationFn: (formData: FormData) => uploadMaterial(formData), onSuccess: () => invalidate(publicInvalidationKeys.journalEntries, publicInvalidationKeys.careerTasks, publicInvalidationKeys.breakdownReadiness, publicInvalidationKeys.analyticsIntelligence, publicInvalidationKeys.analyticsIndustryTrends, publicInvalidationKeys.analyticsMaterialPerformance, publicInvalidationKeys.commandCenter) });
}

export function useUpdateMaterial() {
  const invalidate = useInvalidateMaterials();
  return useMutation({
    mutationFn: ({ assetId, patch }: { assetId: string; patch: Partial<Asset> }) => updateMaterial(assetId, patch),
    onSuccess: (asset) => invalidate(...(asset.asset_type === "Resume" ? [publicInvalidationKeys.journalEntries] : []), publicInvalidationKeys.breakdownReadiness, publicInvalidationKeys.analyticsIntelligence, publicInvalidationKeys.analyticsIndustryTrends, publicInvalidationKeys.analyticsMaterialPerformance)
  });
}

export function useDeleteMaterial() {
  const invalidate = useInvalidateMaterials();
  return useMutation({ mutationFn: (assetId: string) => deleteMaterial(assetId), onSuccess: () => invalidate(publicInvalidationKeys.breakdownReadiness, publicInvalidationKeys.analyticsIntelligence, publicInvalidationKeys.analyticsIndustryTrends, publicInvalidationKeys.analyticsMaterialPerformance) });
}

export function useAnalyzeMaterial() {
  const invalidate = useInvalidateMaterials();
  return useMutation({ mutationFn: (assetId: string) => analyzeMaterial(assetId), onSuccess: () => invalidate(publicInvalidationKeys.breakdownReadiness, publicInvalidationKeys.analyticsIntelligence, publicInvalidationKeys.analyticsIndustryTrends, publicInvalidationKeys.analyticsMaterialPerformance) });
}
