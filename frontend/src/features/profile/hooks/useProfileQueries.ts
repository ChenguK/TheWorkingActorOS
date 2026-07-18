import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { ActingCredit, CastingPlatformSubscription, PlatformAssetMapping, Representation } from "../../../types/domain";
import {
  approvePlatformProfileImport, approvePublicProfileImport, createActingCredit, createPlatformAssetMapping, createRepresentation,
  deleteActingCredit, deletePlatformAssetMapping, deletePlatformProfileImport, deletePublicProfileImport, deleteRepresentation,
  getActorProfile, getProfessionalEquipmentProfile, getTravelPreferences, importProfileUpload, importPublicProfileUrl,
  listActingCredits, listPlatformAssetMappings, listPlatformProfiles, listPlatformSubscriptions, listPublicProfileImports, listRepresentations,
  rejectPlatformProfileImport, rejectPublicProfileImport, saveTravelPreferences, updateActingCredit, updateActorProfile,
  updatePlatformAssetMapping, updatePlatformSubscription, updateProfessionalEquipmentProfile, updateRepresentation
} from "../api";

export const profileKeys = {
  actor: queryKeys.profile.list({ resource: "actor" }), travel: (actorId?: string) => queryKeys.profile.list({ resource: "travel", actorId: actorId ?? null }),
  representations: queryKeys.profile.list({ resource: "representations" }), credits: queryKeys.profile.list({ resource: "actingCredits" }),
  platformProfiles: queryKeys.profile.list({ resource: "platformProfiles" }), publicImports: queryKeys.profile.list({ resource: "publicProfileImports" }),
  mappings: queryKeys.profile.list({ resource: "platformMappings" }), subscriptions: queryKeys.profile.list({ resource: "platformSubscriptions" }),
  equipment: queryKeys.profile.list({ resource: "equipmentProfile" })
} as const;

const queryOptions = { staleTime: queryStaleTimes.workflow };
const importQueryOptions = { ...queryOptions, refetchOnMount: "always" as const };
export const useActorProfile = () => useQuery({ queryKey: profileKeys.actor, queryFn: getActorProfile, ...queryOptions });
export const useTravelPreferences = (actorId?: string) => useQuery({ queryKey: profileKeys.travel(actorId), queryFn: () => getTravelPreferences(actorId!), enabled: Boolean(actorId), ...queryOptions });
export const useRepresentations = () => useQuery({ queryKey: profileKeys.representations, queryFn: listRepresentations, ...queryOptions });
export const useActingCredits = () => useQuery({ queryKey: profileKeys.credits, queryFn: listActingCredits, ...queryOptions });
export const usePlatformProfiles = () => useQuery({ queryKey: profileKeys.platformProfiles, queryFn: listPlatformProfiles, ...importQueryOptions });
export const usePublicProfileImports = () => useQuery({ queryKey: profileKeys.publicImports, queryFn: listPublicProfileImports, ...importQueryOptions });
export const usePlatformAssetMappings = () => useQuery({ queryKey: profileKeys.mappings, queryFn: listPlatformAssetMappings, ...queryOptions });
export const usePlatformSubscriptions = () => useQuery({ queryKey: profileKeys.subscriptions, queryFn: listPlatformSubscriptions, ...queryOptions });
export const useEquipmentProfile = () => useQuery({ queryKey: profileKeys.equipment, queryFn: getProfessionalEquipmentProfile, ...queryOptions });

function useInvalidate(...keys: readonly (readonly unknown[])[]) { const client = useQueryClient(); return () => Promise.all(keys.map((queryKey) => client.invalidateQueries({ queryKey }))); }
export function useUpdateActorProfile() { const invalidate = useInvalidate(profileKeys.actor); return useMutation({ mutationFn: updateActorProfile, onSuccess: invalidate }); }
export function useSaveTravelPreferences(actorId?: string) { const invalidate = useInvalidate(profileKeys.travel(actorId)); return useMutation({ mutationFn: saveTravelPreferences, onSuccess: invalidate }); }
export function useCreateRepresentation() { const invalidate = useInvalidate(profileKeys.representations); return useMutation({ mutationFn: createRepresentation, onSuccess: invalidate }); }
export function useUpdateRepresentation() { const invalidate = useInvalidate(profileKeys.representations); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Partial<Representation> }) => updateRepresentation(id, patch), onSuccess: invalidate }); }
export function useDeleteRepresentation() { const invalidate = useInvalidate(profileKeys.representations); return useMutation({ mutationFn: deleteRepresentation, onSuccess: invalidate }); }
export function useCreateActingCredit() { const invalidate = useInvalidate(profileKeys.credits); return useMutation({ mutationFn: createActingCredit, onSuccess: invalidate }); }
export function useUpdateActingCredit() { const invalidate = useInvalidate(profileKeys.credits); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Partial<ActingCredit> }) => updateActingCredit(id, patch), onSuccess: invalidate }); }
export function useDeleteActingCredit() { const invalidate = useInvalidate(profileKeys.credits); return useMutation({ mutationFn: deleteActingCredit, onSuccess: invalidate }); }
function useInvalidateImports() { return useInvalidate(profileKeys.platformProfiles, profileKeys.publicImports, profileKeys.mappings, profileKeys.credits); }
export function useImportPublicProfile() { const invalidate = useInvalidateImports(); return useMutation({ mutationFn: importPublicProfileUrl, onSuccess: invalidate }); }
export function useImportProfileUpload() { const invalidate = useInvalidateImports(); return useMutation({ mutationFn: importProfileUpload, onSuccess: invalidate }); }
export function usePublicImportAction() { const invalidate = useInvalidateImports(); return useMutation({ mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" | "delete" }) => action === "approve" ? approvePublicProfileImport(id) : action === "reject" ? rejectPublicProfileImport(id) : deletePublicProfileImport(id), onSuccess: invalidate }); }
export function usePlatformImportAction() { const invalidate = useInvalidateImports(); return useMutation({ mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" | "delete" }) => action === "approve" ? approvePlatformProfileImport(id) : action === "reject" ? rejectPlatformProfileImport(id) : deletePlatformProfileImport(id), onSuccess: invalidate }); }
export function useCreatePlatformMapping() { const invalidate = useInvalidate(profileKeys.mappings); return useMutation({ mutationFn: createPlatformAssetMapping, onSuccess: invalidate }); }
export function useUpdatePlatformMapping() { const invalidate = useInvalidate(profileKeys.mappings); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Partial<PlatformAssetMapping> }) => updatePlatformAssetMapping(id, patch), onSuccess: invalidate }); }
export function useDeletePlatformMapping() { const invalidate = useInvalidate(profileKeys.mappings); return useMutation({ mutationFn: deletePlatformAssetMapping, onSuccess: invalidate }); }
export function useUpdatePlatformSubscription() { const invalidate = useInvalidate(profileKeys.subscriptions); return useMutation({ mutationFn: ({ id, patch }: { id: string; patch: Partial<CastingPlatformSubscription> }) => updatePlatformSubscription(id, patch), onSuccess: invalidate }); }
export function useUpdateEquipmentProfile() { const invalidate = useInvalidate(profileKeys.equipment); return useMutation({ mutationFn: updateProfessionalEquipmentProfile, onSuccess: invalidate }); }
