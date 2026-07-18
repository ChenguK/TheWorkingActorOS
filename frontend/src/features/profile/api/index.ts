import { api, generatedResumeDocxUrl, generatedResumePdfUrl } from "../../../services/api";
import type {
  ActingCredit,
  ActorProfile,
  CastingPlatformSubscription,
  ProfessionalEquipmentProfile,
  PlatformAssetMapping,
  PlatformProfile,
  PublicProfileImport,
  Representation,
  TravelPreference
} from "../../../types/domain";

export function getActorProfile() {
  return api.get<ActorProfile | null>("/actor-profile");
}

export const getProfile = getActorProfile;

export function updateActorProfile(payload: unknown) {
  return api.put<ActorProfile>("/actor-profile", payload);
}

export function updateProfessionalEquipmentProfile(payload: unknown) {
  return api.put<ProfessionalEquipmentProfile>("/operations/equipment-profile", payload);
}

export function getProfessionalEquipmentProfile() {
  return api.get<ProfessionalEquipmentProfile | null>("/operations/equipment-profile");
}

export function getTravelPreferences(actorProfileId: string) {
  return api.get<TravelPreference | null>(`/travel-preferences/${actorProfileId}`);
}

export const updateTravelPreferences = (actorProfileId: string, patch: unknown) =>
  api.patch<TravelPreference>(`/travel-preferences/${actorProfileId}`, patch);

export function saveTravelPreferences(payload: unknown) {
  return api.put<TravelPreference>("/travel-preferences", payload);
}

export function createRepresentation(payload: unknown) {
  return api.post<Representation>("/representation", payload);
}

export function listRepresentations() {
  return api.get<Representation[]>("/representation");
}

export function updateRepresentation(representationId: string, patch: unknown) {
  return api.patch<Representation>(`/representation/${representationId}`, patch);
}

export function deleteRepresentation(representationId: string) {
  return api.delete(`/representation/${representationId}`);
}

export function createActingCredit(payload: unknown) {
  return api.post<ActingCredit>("/representation/acting-credits", payload);
}

export function listActingCredits() {
  return api.get<ActingCredit[]>("/representation/acting-credits/list");
}

export const createCredit = createActingCredit;

export function updateActingCredit(creditId: string, patch: unknown) {
  return api.patch(`/representation/acting-credits/${creditId}`, patch);
}

export const updateCredit = updateActingCredit;

export function deleteActingCredit(creditId: string) {
  return api.delete(`/representation/acting-credits/${creditId}`);
}

export const deleteCredit = deleteActingCredit;

export function importPublicProfileUrl(payload: unknown) {
  return api.post<PublicProfileImport>("/platform-imports/public-profiles/import-url", payload);
}

export function listPlatformProfiles() {
  return api.get<PlatformProfile[]>("/platform-imports/profiles");
}

export function listPublicProfileImports() {
  return api.get<PublicProfileImport[]>("/platform-imports/public-profiles");
}

export function listPlatformAssetMappings() {
  return api.get<PlatformAssetMapping[]>("/platform-imports/asset-mappings");
}

export function listPlatformSubscriptions() {
  return api.get<CastingPlatformSubscription[]>("/operations/platform-subscriptions");
}

export function importProfileUpload(formData: FormData) {
  return api.upload<PlatformProfile>("/platform-imports/profiles/import-upload", formData);
}

export function approvePublicProfileImport(importId: string) {
  return api.post(`/platform-imports/public-profiles/${importId}/approve`);
}

export function rejectPublicProfileImport(importId: string) {
  return api.post(`/platform-imports/public-profiles/${importId}/reject`);
}

export function deletePublicProfileImport(importId: string) {
  return api.delete(`/platform-imports/public-profiles/${importId}`);
}

export function approvePlatformProfileImport(profileId: string) {
  return api.post(`/platform-imports/profiles/${profileId}/approve`);
}

export function rejectPlatformProfileImport(profileId: string) {
  return api.post(`/platform-imports/profiles/${profileId}/reject`);
}

export function deletePlatformProfileImport(profileId: string) {
  return api.delete(`/platform-imports/profiles/${profileId}`);
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

export function updatePlatformSubscription(subscriptionId: string, patch: Partial<CastingPlatformSubscription>) {
  return api.patch<CastingPlatformSubscription>(`/operations/platform-subscriptions/${subscriptionId}`, patch);
}

export { generatedResumeDocxUrl, generatedResumePdfUrl };
