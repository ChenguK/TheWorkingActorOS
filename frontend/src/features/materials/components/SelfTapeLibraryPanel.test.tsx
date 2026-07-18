import { describe, expect, it, vi } from "vitest";
import { renderWithRouter, screen } from "../../../test/testUtils";
import { SelfTapeLibraryPanel } from "./SelfTapeLibraryPanel";
import * as reusableHooks from "../hooks/useReusableSelfTapes";

vi.mock("../hooks/useReusableSelfTapes", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../hooks/useReusableSelfTapes")>();
  return {
    ...actual,
    useReusableSelfTapes: vi.fn(),
    useReusableSelfTapeAnalytics: vi.fn(),
    useCreateReusableSelfTape: vi.fn(() => ({ mutateAsync: vi.fn(), error: null, isPending: false })),
    useUpdateReusableSelfTape: vi.fn(() => ({ mutateAsync: vi.fn(), error: null, isPending: false })),
    useDeleteReusableSelfTape: vi.fn(() => ({ mutateAsync: vi.fn(), error: null, isPending: false }))
  };
});

const tape = {
  id: "tape-1", title: "Authority", role_type: "Doctor", archetypes: ["Authority"],
  file_path: "/media/authority.mp4", linked_opportunity_id: null, linked_submission_id: null,
  outcome: "Callback", notes: "Strong take", date_created: "2026-07-01",
  created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z"
};

function query(overrides: Record<string, unknown> = {}) {
  return { data: undefined, isLoading: false, isError: false, isRefetching: false, ...overrides };
}

function renderPanel() {
  return renderWithRouter(<SelfTapeLibraryPanel opportunities={[]} submissions={[]} />);
}

describe("SelfTapeLibraryPanel", () => {
  it("shows independent initial loading states", () => {
    vi.mocked(reusableHooks.useReusableSelfTapes).mockReturnValue(query({ isLoading: true }) as never);
    vi.mocked(reusableHooks.useReusableSelfTapeAnalytics).mockReturnValue(query({ isLoading: true }) as never);
    renderPanel();
    expect(screen.getByText("Loading reusable self-tapes...")).toBeInTheDocument();
    expect(screen.getByText("Loading reusable self-tape analytics...")).toBeInTheDocument();
  });

  it("shows the empty library without treating insufficient analytics as an error", () => {
    vi.mocked(reusableHooks.useReusableSelfTapes).mockReturnValue(query({ data: [] }) as never);
    vi.mocked(reusableHooks.useReusableSelfTapeAnalytics).mockReturnValue(query({ data: { by_archetype: [], by_outcome: [], best_performing_tapes: [], underused_tapes: [] } }) as never);
    renderPanel();
    expect(screen.getByText("No self-tapes in the library yet.")).toBeInTheDocument();
    expect(screen.getAllByText("Not enough data")).toHaveLength(2);
  });

  it("keeps cached library records visible when analytics fails", () => {
    vi.mocked(reusableHooks.useReusableSelfTapes).mockReturnValue(query({ data: [tape], isRefetching: true }) as never);
    vi.mocked(reusableHooks.useReusableSelfTapeAnalytics).mockReturnValue(query({ isError: true }) as never);
    renderPanel();
    expect(screen.getByRole("heading", { name: "Authority" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Library records remain available");
    expect(screen.getByText("Refreshing reusable self-tapes...")).toBeInTheDocument();
  });

  it("shows a library error independently from successful analytics", () => {
    vi.mocked(reusableHooks.useReusableSelfTapes).mockReturnValue(query({ isError: true }) as never);
    vi.mocked(reusableHooks.useReusableSelfTapeAnalytics).mockReturnValue(query({ data: { by_archetype: [{ archetype: "Authority", count: 1 }], by_outcome: [], best_performing_tapes: [tape], underused_tapes: [] } }) as never);
    renderPanel();
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load the reusable self-tape library");
    expect(screen.getByText("Authority (1)")).toBeInTheDocument();
  });
});
