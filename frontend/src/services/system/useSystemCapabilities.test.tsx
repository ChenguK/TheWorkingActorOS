import { createTestQueryClient, createTestQueryWrapper, renderHook, waitFor } from "../../test/testUtils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryKeys } from "../api/queryKeys";
import * as api from "./api";
import { systemCapabilitiesKey, useSystemCapabilities } from "./useSystemCapabilities";

vi.mock("./api", () => ({ getSystemCapabilities: vi.fn() }));
const capabilities = { flags: {}, states: {}, integrations: [], labels: {} } as never;

describe("shared system capabilities", () => {
  beforeEach(() => vi.clearAllMocks());

  it("uses the deterministic infrastructure key", () => {
    expect(systemCapabilitiesKey).toBe(queryKeys.system.capabilities);
    expect(systemCapabilitiesKey).toEqual(["system", "capabilities"]);
  });

  it("loads capabilities and deduplicates consumers on one cache", async () => {
    vi.mocked(api.getSystemCapabilities).mockResolvedValue(capabilities);
    const client = createTestQueryClient(); const wrapper = createTestQueryWrapper(client);
    const first = renderHook(() => useSystemCapabilities(), { wrapper });
    const second = renderHook(() => useSystemCapabilities(), { wrapper });
    await waitFor(() => expect(first.result.current.data).toEqual(capabilities));
    expect(second.result.current.data).toEqual(capabilities);
    expect(api.getSystemCapabilities).toHaveBeenCalledTimes(1);
  });

  it("preserves capability API errors", async () => {
    vi.mocked(api.getSystemCapabilities).mockRejectedValue(new Error("capabilities unavailable"));
    const { result } = renderHook(() => useSystemCapabilities(), { wrapper: createTestQueryWrapper() });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toContain("capabilities unavailable");
  });
});
