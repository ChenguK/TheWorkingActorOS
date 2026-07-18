import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../services/api/errors";
import { createQueryClient, shouldRetryQuery } from "./queryClient";
import { clearTestQueryClients, createTestQueryClient } from "../test/testUtils";

describe("query client policy", () => {
  it("retries transient errors once but not validation or permission errors", () => {
    expect(shouldRetryQuery(0, new ApiError({ message: "offline", retryable: true }))).toBe(true);
    expect(shouldRetryQuery(1, new ApiError({ message: "offline", retryable: true }))).toBe(false);
    expect(shouldRetryQuery(0, new ApiError({ message: "busy", status: 503, retryable: true }))).toBe(true);
    expect(shouldRetryQuery(0, new ApiError({ message: "invalid", status: 422 }))).toBe(false);
    expect(shouldRetryQuery(0, new ApiError({ message: "forbidden", status: 403 }))).toBe(false);
    expect(shouldRetryQuery(0, new ApiError({ message: "rate limited", status: 429, retryable: true }))).toBe(true);
  });

  it("does not retry queries in the test client", async () => {
    const client = createTestQueryClient();
    const queryFn = vi.fn(async () => Promise.reject(new Error("failure")));

    await expect(client.fetchQuery({ queryKey: ["retry-test"], queryFn })).rejects.toThrow("failure");

    expect(queryFn).toHaveBeenCalledTimes(1);
    client.clear();
  });

  it("creates isolated test caches", () => {
    const first = createTestQueryClient();
    const second = createTestQueryClient();
    first.setQueryData(["isolation"], { value: 1 });

    expect(first.getQueryData(["isolation"])).toEqual({ value: 1 });
    expect(second.getQueryData(["isolation"])).toBeUndefined();
    first.clear();
    second.clear();
  });

  it("clears all shared-factory test caches during test cleanup", () => {
    const client = createTestQueryClient();
    client.setQueryData(["cleanup"], "cached");

    clearTestQueryClients();

    expect(client.getQueryData(["cleanup"])).toBeUndefined();
  });

  it("keeps mutation errors and disables automatic mutation retries", () => {
    const client = createQueryClient();
    expect(client.getDefaultOptions().mutations?.retry).toBe(false);
    expect(client.getDefaultOptions().queries?.refetchOnWindowFocus).toBe(false);
    expect(client.getDefaultOptions().queries?.refetchOnReconnect).toBe(true);
    expect(client.getDefaultOptions().queries?.gcTime).toBe(10 * 60_000);
    client.clear();
  });
});
