import { beforeEach, describe, expect, it, vi } from "vitest";
import { SourceLibraryPanel } from "./SourceLibraryPanel";
import { renderWithRouter, screen, waitFor } from "../../../test/testUtils";
import type { SourceResearchItem } from "../../../types/domain";
import { approveSource, createSource, findNewSources, listSources, rejectSource, updateSource } from "../api";

vi.mock("../api", () => ({
  approveSource: vi.fn(),
  createSource: vi.fn(),
  findNewSources: vi.fn(),
  listArchivedSources: vi.fn(),
  listSources: vi.fn(),
  rejectSource: vi.fn(),
  restoreSource: vi.fn(),
  updateSource: vi.fn()
}));

function sourceFixture(overrides: Partial<SourceResearchItem> = {}): SourceResearchItem {
  return {
    id: "source-1", name: "Example Casting", source_url: "https://example.com/casting", base_url: "https://example.com",
    suggested_specific_url: null, approved_discovery_url: "https://example.com/casting", category: "Public casting site", status: "Active",
    reliability_notes: null, user_rating: null, last_researched_date: null, last_checked_date: null, notes: "Posts public acting breakdowns.",
    suggested_by_ai: false, approved_by_user: true, deleted: false, deleted_at: null, rejection_reason: null, rejected_by_user: false,
    previous_status: null, provider_key: null, added_to_discovery_at: null, source_health: "Active", suggested_classification: "Valid Breakdown Source",
    health_reason: null, http_status: 200, page_title: "Example Casting Calls", redirect_target: null, visible_text_excerpt: null,
    organization_name: null, submitted_url: "https://example.com/casting", final_resolved_url: "https://example.com/casting",
    url_health_status: "Active", organization_legitimacy: "Unverified Organization", source_usefulness: "Useful Breakdown Source",
    source_classification: "Valid Breakdown Source", verification_notes: null, discovered_from_breakdown_id: null, discovery_reason: null,
    source_role_match_count: 0, created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z", ...overrides
  };
}

describe("SourceLibraryPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listSources).mockResolvedValue([sourceFixture()]);
    vi.mocked(approveSource).mockImplementation(async (sourceId) => sourceFixture({ id: sourceId, status: "Active", approved_by_user: true }));
    vi.mocked(createSource).mockResolvedValue(sourceFixture());
    vi.mocked(findNewSources).mockResolvedValue([]);
    vi.mocked(rejectSource).mockImplementation(async (sourceId, reason) => sourceFixture({ id: sourceId, deleted: true, rejected_by_user: true, rejection_reason: reason ?? null }));
    vi.mocked(updateSource).mockImplementation(async (sourceId, patch) => sourceFixture({ id: sourceId, ...patch }));
  });

  it("shows initial loading and renders the source list", async () => {
    let resolveSources: (sources: SourceResearchItem[]) => void = () => undefined;
    vi.mocked(listSources).mockReturnValue(new Promise((resolve) => { resolveSources = resolve; }));
    renderWithRouter(<SourceLibraryPanel />);
    expect(screen.getByText("Loading source library…")).toBeInTheDocument();
    resolveSources([sourceFixture()]);
    expect(await screen.findByRole("link", { name: "Example Casting" })).toBeInTheDocument();
  });

  it("shows the initial API error without rendering empty queues", async () => {
    vi.mocked(listSources).mockRejectedValue(new Error("Source service unavailable"));
    renderWithRouter(<SourceLibraryPanel />);
    expect(await screen.findByText("Source service unavailable")).toBeInTheDocument();
    expect(screen.queryByText("No approved breakdown sources yet.")).not.toBeInTheDocument();
  });

  it("classifies suggested sources into approval filters", async () => {
    vi.mocked(listSources).mockResolvedValue([sourceFixture({ status: "Suggested", approved_by_user: false, source_classification: "Casting Office" })]);
    renderWithRouter(<SourceLibraryPanel />);
    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.getByText("Useful for relationship tracking, not daily breakdown scraping unless a public breakdown page is found.")).toBeInTheDocument();
  });

  it("opens the edit form and saves through the mutation hook without a browser prompt", async () => {
    const promptSpy = vi.spyOn(window, "prompt");
    const { user } = renderWithRouter(<SourceLibraryPanel />);
    await user.click(await screen.findByRole("button", { name: "Edit" }));
    expect(promptSpy).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText("Source Name"));
    await user.type(screen.getByLabelText("Source Name"), "Updated Casting");
    await user.click(screen.getByRole("button", { name: "Save Source" }));
    await waitFor(() => expect(updateSource).toHaveBeenCalledWith("source-1", expect.objectContaining({ name: "Updated Casting" })));
  });

  it("creates a source through the feature mutation", async () => {
    const { user } = renderWithRouter(<SourceLibraryPanel />);
    await user.click(await screen.findByRole("button", { name: "Add Source" }));
    await user.type(screen.getByLabelText("Source Name"), "New Casting Site");
    await user.click(screen.getByRole("button", { name: "Save Source" }));
    await waitFor(() => expect(createSource).toHaveBeenCalledWith(expect.objectContaining({ name: "New Casting Site", status: "Researching" })));
  });

  it("activates and pauses through focused update mutations", async () => {
    vi.mocked(listSources).mockResolvedValue([sourceFixture({ status: "Paused" })]);
    const { user } = renderWithRouter(<SourceLibraryPanel />);
    await user.click(await screen.findByRole("button", { name: "Activate" }));
    await waitFor(() => expect(approveSource).toHaveBeenCalledWith("source-1"));
  });

  it("approves a suggested source through review and activation", async () => {
    vi.mocked(listSources).mockResolvedValue([sourceFixture({ id: "source-2", name: "Suggested Film Board", status: "Suggested", approved_by_user: false })]);
    const { user } = renderWithRouter(<SourceLibraryPanel />);
    await user.click(await screen.findByRole("button", { name: "Approve" }));
    await waitFor(() => expect(updateSource).toHaveBeenCalledWith("source-2", expect.objectContaining({ approved_by_user: true })));
    expect(approveSource).toHaveBeenCalledWith("source-2");
  });

  it("rejects a source and immediately hides it from the ordinary view", async () => {
    vi.mocked(listSources).mockResolvedValue([sourceFixture({ status: "Suggested", approved_by_user: false })]);
    const { user } = renderWithRouter(<SourceLibraryPanel />);
    await user.click(await screen.findByRole("button", { name: "Reject" }));
    await waitFor(() => expect(rejectSource).toHaveBeenCalledWith("source-1", "Rejected by user."));
    expect(screen.queryByRole("link", { name: "Example Casting" })).not.toBeInTheDocument();
    expect(vi.mocked(rejectSource).mock.results[0]?.value).toBeInstanceOf(Promise);
  });

  it("discovers new sources without making a global refresh call", async () => {
    vi.mocked(findNewSources).mockResolvedValue([sourceFixture({ id: "source-3" })]);
    const { user } = renderWithRouter(<SourceLibraryPanel />);
    await user.click(await screen.findByRole("button", { name: "Find New Breakdown Sources" }));
    await waitFor(() => expect(findNewSources).toHaveBeenCalledWith(undefined));
    expect(await screen.findByText("1 new breakdown source added for your approval.")).toBeInTheDocument();
  });
});
