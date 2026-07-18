import { useQueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";
import { render, screen } from "../../test/testUtils";
import { AppProviders } from "./AppProviders";
import { queryClient } from "../queryClient";

function QueryConsumer() {
  const client = useQueryClient();
  return <p>{client === queryClient ? "Shared query client" : "Unexpected query client"}</p>;
}

describe("AppProviders", () => {
  it("renders children inside the server-state provider", () => {
    render(<AppProviders><QueryConsumer /></AppProviders>);

    expect(screen.getByText("Shared query client")).toBeInTheDocument();
  });

  it("keeps the production QueryClient stable across provider renders", () => {
    const firstReference = queryClient;
    const { rerender } = render(<AppProviders><QueryConsumer /></AppProviders>);
    rerender(<AppProviders><QueryConsumer /></AppProviders>);

    expect(queryClient).toBe(firstReference);
    expect(screen.getByText("Shared query client")).toBeInTheDocument();
  });
});
