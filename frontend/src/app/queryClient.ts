import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "../services/api/errors";
export { queryStaleTimes } from "../services/api/queryPolicy";

export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (isApiError(error)) {
    if (error.status !== null && error.status >= 400 && error.status < 500) {
      return error.retryable && (error.status === 408 || error.status === 429) && failureCount < 1;
    }
    return error.retryable && failureCount < 1;
  }
  return failureCount < 1;
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        gcTime: 10 * 60_000,
        refetchOnReconnect: true,
        refetchOnWindowFocus: false,
        retry: shouldRetryQuery
      },
      mutations: {
        retry: false
      }
    }
  });
}

export const queryClient = createQueryClient();
