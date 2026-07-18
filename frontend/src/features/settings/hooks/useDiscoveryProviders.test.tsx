import { act, createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { systemCapabilitiesKey } from "../../../services/system";
import * as api from "../api";
import { settingsKeys, useDiscoveryProviders } from "./useDiscoveryProviders";
import { queryKeys } from "../../../services/api/queryKeys";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, listDiscoveryProviders: vi.fn(), updateDiscoveryProvider: vi.fn(), healthCheckDiscoveryProvider: vi.fn() };
});
const provider = { provider_key: "public-web", display_name: "Public Web Search", category: "Public", tier: 2, health_status: "Healthy" } as never;

describe("Settings provider queries", () => {
  beforeEach(() => vi.clearAllMocks());
  it("uses a deterministic Settings-owned provider key", () => {
    expect(settingsKeys.discoveryProviders).toEqual(queryKeys.settings.list({ resource: "discoveryProviders" }));
  });
  it("loads providers and preserves API errors", async () => {
    vi.mocked(api.listDiscoveryProviders).mockResolvedValueOnce([provider]);
    const loaded = renderHook(() => useDiscoveryProviders(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(loaded.result.current.providers).toEqual([provider]));
    vi.mocked(api.listDiscoveryProviders).mockRejectedValueOnce(new Error("providers unavailable"));
    const failed = renderHook(() => useDiscoveryProviders(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(failed.result.current.error).toBeTruthy());
  });
  it("invalidates providers and shared capabilities after configuration update", async () => {
    vi.mocked(api.listDiscoveryProviders).mockResolvedValue([provider]); vi.mocked(api.updateDiscoveryProvider).mockResolvedValue(provider);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDiscoveryProviders(), { wrapper: createTestQueryWrapper(client) });
    await waitFor(() => expect(result.current.providers).toHaveLength(1));
    await act(() => result.current.updateProvider(provider, { enabled: false }));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: settingsKeys.discoveryProviders });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: systemCapabilitiesKey });
  });
  it("refreshes provider state without invalidating capabilities after health check", async () => {
    vi.mocked(api.listDiscoveryProviders).mockResolvedValue([provider]); vi.mocked(api.healthCheckDiscoveryProvider).mockResolvedValue(provider);
    const client = createTestQueryClient(); const invalidate = vi.spyOn(client, "invalidateQueries");
    const { result } = renderHook(() => useDiscoveryProviders(), { wrapper: createTestQueryWrapper(client) });
    await waitFor(() => expect(result.current.providers).toHaveLength(1));
    await act(() => result.current.healthCheck(provider));
    expect(invalidate).toHaveBeenCalledWith({ queryKey: settingsKeys.discoveryProviders });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: systemCapabilitiesKey });
  });
});
