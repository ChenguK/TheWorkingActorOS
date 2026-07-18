import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement, ReactNode } from "react";

const testQueryClients = new Set<QueryClient>();

export function createTestQueryClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { gcTime: Infinity, retry: false },
      mutations: { retry: false }
    }
  });
  testQueryClients.add(queryClient);
  return queryClient;
}

export function clearTestQueryClients() {
  testQueryClients.forEach((queryClient) => queryClient.clear());
  testQueryClients.clear();
}

export function createTestQueryWrapper(queryClient = createTestQueryClient()) {
  return function TestQueryWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

export function renderWithRouter(
  ui: ReactElement,
  {
    route = "/",
    ...options
  }: RenderOptions & {
    route?: string;
  } = {}
) {
  const queryClient = createTestQueryClient();
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return {
    user: userEvent.setup(),
    queryClient,
    ...render(ui, { wrapper: Wrapper, ...options })
  };
}

export * from "@testing-library/react";
export { userEvent };
