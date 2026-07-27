import { act, createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { invalidationContracts, keysForContract } from "../../../services/api/invalidationContracts";
import { queryKeys } from "../../../services/api/queryKeys";
import * as api from "../api";
import {
  profileKeys, useActorProfile, useCreateActingCredit, useCreatePlatformMapping, useCreateRepresentation, useImportProfileUpload,
  usePlatformImportAction, usePublicImportAction, useSaveTravelPreferences, useUpdateActorProfile, useUpdateEquipmentProfile,
  useUpdatePlatformSubscription
} from "./useProfileQueries";

vi.mock("../api", () => ({
  approvePlatformProfileImport: vi.fn(), approvePublicProfileImport: vi.fn(), createActingCredit: vi.fn(), createPlatformAssetMapping: vi.fn(),
  createRepresentation: vi.fn(), deleteActingCredit: vi.fn(), deletePlatformAssetMapping: vi.fn(), deletePlatformProfileImport: vi.fn(),
  deletePublicProfileImport: vi.fn(), deleteRepresentation: vi.fn(), getActorProfile: vi.fn(), getProfessionalEquipmentProfile: vi.fn(),
  getTravelPreferences: vi.fn(), importProfileUpload: vi.fn(), importPublicProfileUrl: vi.fn(), listActingCredits: vi.fn(),
  listPlatformAssetMappings: vi.fn(), listPlatformProfiles: vi.fn(), listPlatformSubscriptions: vi.fn(), listPublicProfileImports: vi.fn(),
  listRepresentations: vi.fn(), rejectPlatformProfileImport: vi.fn(), rejectPublicProfileImport: vi.fn(), saveTravelPreferences: vi.fn(),
  updateActingCredit: vi.fn(), updateActorProfile: vi.fn(), updatePlatformAssetMapping: vi.fn(), updatePlatformSubscription: vi.fn(),
  updateProfessionalEquipmentProfile: vi.fn(), updateRepresentation: vi.fn()
}));

function mutationHarness<T>(hook: () => { mutateAsync: (value: T) => Promise<unknown> }) {
  const client = createTestQueryClient();
  const invalidate = vi.spyOn(client, "invalidateQueries");
  const result = renderHook(hook, { wrapper: createTestQueryWrapper(client) }).result;
  return { invalidate, result };
}

describe("Profile query boundaries", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses deterministic resource keys", () => {
    expect(profileKeys.actor).toEqual(queryKeys.profile.list({ resource: "actor" }));
    expect(profileKeys.travel("actor-1")).toEqual(queryKeys.profile.list({ resource: "travel", actorId: "actor-1" }));
    expect(profileKeys.mappings).not.toEqual(profileKeys.platformProfiles);
  });

  it("keeps a fresh actor profile across an immediate remount", async () => {
    const actor = { id: "actor-1", name: "Actor" } as never;
    vi.mocked(api.getActorProfile).mockResolvedValue(actor);
    const client = createTestQueryClient();
    const wrapper = createTestQueryWrapper(client);
    const first = renderHook(() => useActorProfile(), { wrapper });
    await waitFor(() => expect(first.result.current.data).toEqual(actor));
    first.unmount();
    const second = renderHook(() => useActorProfile(), { wrapper });
    await waitFor(() => expect(second.result.current.data).toEqual(actor));
    expect(api.getActorProfile).toHaveBeenCalledTimes(1);
  });

  it.each([
    ["travel", () => useSaveTravelPreferences("actor-1"), () => vi.mocked(api.saveTravelPreferences).mockResolvedValue({} as never), { actor_profile_id: "actor-1" }, profileKeys.travel("actor-1")],
    ["representation", () => useCreateRepresentation(), () => vi.mocked(api.createRepresentation).mockResolvedValue({} as never), { agency_name: "Agency" }, profileKeys.representations],
    ["credit", () => useCreateActingCredit(), () => vi.mocked(api.createActingCredit).mockResolvedValue({} as never), { category: "Film" }, profileKeys.credits],
    ["mapping", () => useCreatePlatformMapping(), () => vi.mocked(api.createPlatformAssetMapping).mockResolvedValue({} as never), { platform_asset_name: "Headshot" }, profileKeys.mappings],
    ["subscription", () => useUpdatePlatformSubscription(), () => vi.mocked(api.updatePlatformSubscription).mockResolvedValue({} as never), { id: "sub-1", patch: { active: true } }, profileKeys.subscriptions],
    ["equipment", () => useUpdateEquipmentProfile(), () => vi.mocked(api.updateProfessionalEquipmentProfile).mockResolvedValue({} as never), { cameras: ["Phone"] }, profileKeys.equipment]
  ] as const)("invalidates only the focused %s resource", async (_name, hook, prepare, payload, key) => {
    prepare();
    const { invalidate, result } = mutationHarness(hook as never);
    await act(async () => result.current.mutateAsync(payload as never));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: [] });
  });

  it("invalidates only import-affected Profile records after an upload", async () => {
    vi.mocked(api.importProfileUpload).mockResolvedValue({} as never);
    const { invalidate, result } = mutationHarness(() => useImportProfileUpload());
    await act(async () => result.current.mutateAsync(new FormData()));
    expect(invalidate).toHaveBeenCalledTimes(4);
    for (const key of [profileKeys.platformProfiles, profileKeys.publicImports, profileKeys.mappings, profileKeys.credits]) {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
    }
  });

  it("uses the exact actor-profile update contract after success", async () => {
    vi.mocked(api.updateActorProfile).mockResolvedValue({} as never);
    const { invalidate, result } = mutationHarness(() => useUpdateActorProfile());
    await act(async () => result.current.mutateAsync({ name: "Actor" } as never));
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toEqual(
      keysForContract(invalidationContracts.actorProfileUpdate)
    );
  });

  it("invalidates nothing after an actor-profile update failure", async () => {
    vi.mocked(api.updateActorProfile).mockRejectedValue(new Error("profile update failed"));
    const { invalidate, result } = mutationHarness(() => useUpdateActorProfile());
    await act(async () => {
      await expect(result.current.mutateAsync({ name: "Actor" } as never)).rejects.toThrow("profile update failed");
    });
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("uses the exact actor-linked platform approval contract after success", async () => {
    vi.mocked(api.approvePlatformProfileImport).mockResolvedValue({} as never);
    const { invalidate, result } = mutationHarness(() => usePlatformImportAction());
    await act(async () => result.current.mutateAsync({ id: "profile-1", action: "approve" }));
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toEqual(
      keysForContract(invalidationContracts.actorLinkedPlatformProfileApprove)
    );
  });

  it("invalidates nothing after an actor-linked platform approval failure", async () => {
    vi.mocked(api.approvePlatformProfileImport).mockRejectedValue(new Error("approval failed"));
    const { invalidate, result } = mutationHarness(() => usePlatformImportAction());
    await act(async () => {
      await expect(result.current.mutateAsync({ id: "profile-1", action: "approve" })).rejects.toThrow("approval failed");
    });
    expect(invalidate).not.toHaveBeenCalled();
  });

  it("keeps public-profile approval separate from actor-linked state", async () => {
    vi.mocked(api.approvePublicProfileImport).mockResolvedValue({} as never);
    const { invalidate, result } = mutationHarness(() => usePublicImportAction());
    await act(async () => result.current.mutateAsync({ id: "public-1", action: "approve" }));
    expect(invalidate.mock.calls.map(([filters]) => filters?.queryKey)).toEqual([
      profileKeys.publicImports,
      profileKeys.mappings
    ]);
    for (const key of [profileKeys.platformProfiles, profileKeys.actor, profileKeys.credits]) {
      expect(invalidate).not.toHaveBeenCalledWith({ queryKey: key });
    }
  });
});
