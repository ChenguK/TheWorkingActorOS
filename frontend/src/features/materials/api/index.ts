import { api, assetFileUrl } from "../../../services/api";
import type { Asset, MaterialOpportunityMatch, PlatformAssetMapping, PlatformProfile, PublicProfileImport, SelfTape, SelfTapeAnalytics } from "../../../types/domain";

export type ReusableSelfTapeCreate = Omit<SelfTape, "id" | "created_at" | "updated_at">;
export type ReusableSelfTapeUpdate = Partial<ReusableSelfTapeCreate>;

export function listMaterials() {
  return api.get<Asset[]>("/assets");
}

export function uploadMaterial(formData: FormData) {
  return api.upload<Asset>("/assets", formData);
}

export function updateMaterial(assetId: string, patch: unknown) {
  return api.patch<Asset>(`/assets/${assetId}`, patch);
}

export function deleteMaterial(assetId: string) {
  return api.delete(`/assets/${assetId}`);
}

export function analyzeMaterial(assetId: string) {
  return api.post(`/assets/${assetId}/analyze`);
}

export function createSelfTape(payload: ReusableSelfTapeCreate) {
  return api.post<SelfTape>("/intelligence/self-tapes", payload);
}

export function listReusableSelfTapes() {
  return api.get<SelfTape[]>("/intelligence/self-tapes");
}

export function getReusableSelfTapeAnalytics() {
  return api.get<SelfTapeAnalytics>("/intelligence/self-tapes/analytics");
}

export function updateSelfTape(selfTapeId: string, patch: ReusableSelfTapeUpdate) {
  return api.patch<SelfTape>(`/intelligence/self-tapes/${selfTapeId}`, patch);
}

export function deleteSelfTape(selfTapeId: string) {
  return api.delete(`/intelligence/self-tapes/${selfTapeId}`);
}

export function findMaterialMatches(query: string) {
  return api.get<MaterialOpportunityMatch[]>(`/opportunities/material-matches?${query}`);
}

export function importPublicProfileUrl(payload: unknown) {
  return api.post<PublicProfileImport>("/platform-imports/public-profiles/import-url", payload);
}

export function importProfileUpload(formData: FormData) {
  return api.upload<PlatformProfile>("/platform-imports/profiles/import-upload", formData);
}

export function createPlatformAssetMapping(payload: unknown) {
  return api.post<PlatformAssetMapping>("/platform-imports/asset-mappings", payload);
}

export function updatePlatformAssetMapping(mappingId: string, patch: unknown) {
  return api.patch<PlatformAssetMapping>(`/platform-imports/asset-mappings/${mappingId}`, patch);
}

export function deletePlatformAssetMapping(mappingId: string) {
  return api.delete(`/platform-imports/asset-mappings/${mappingId}`);
}

export { assetFileUrl };
