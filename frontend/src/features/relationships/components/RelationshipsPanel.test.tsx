import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../services/api/errors";
import { fireEvent, renderWithRouter, screen, waitFor, within } from "../../../test/testUtils";
import type { ActorRelationship, CommunicationLog, RelationshipAnalytics } from "../../../types/domain";
import {
  createCommunicationLog,
  createRelationship,
  deleteCommunicationLog,
  deleteRelationship,
  getRelationshipAnalytics,
  listCommunicationLogs,
  listRelationships,
  updateCommunicationLog,
  updateRelationship
} from "../api";
import { RelationshipsPanel } from "./RelationshipsPanel";

vi.mock("../api", () => ({
  createCommunicationLog: vi.fn(), createRelationship: vi.fn(), deleteCommunicationLog: vi.fn(), deleteRelationship: vi.fn(),
  getRelationshipAnalytics: vi.fn(), listCommunicationLogs: vi.fn(), listRelationships: vi.fn(),
  updateCommunicationLog: vi.fn(), updateRelationship: vi.fn()
}));

const relationship: ActorRelationship = {
  id: "relationship-1", name: "Morgan Lee", role_title: "Casting Director", company_office: "Atlas Casting",
  projects: ["North Star"], notes: "Warm introduction", last_contact_date: "2026-07-10", relationship_strength: "Strong",
  linked_outcomes: ["Callback"], linked_opportunity_ids: [], linked_submission_ids: [],
  created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z"
};
const interaction: CommunicationLog = {
  id: "log-1", date: "2026-07-12", topic: "North Star follow-up", notes: "Sent updated reel", follow_up_needed: true,
  follow_up_date: "2026-07-20", created_at: "2026-07-12T00:00:00Z", updated_at: "2026-07-12T00:00:00Z"
};
const analytics: RelationshipAnalytics = { rows: [], strongest_relationships: [], relationship_agent_explanation: "Track trusted contacts." };

function renderPanel() {
  return renderWithRouter(<RelationshipsPanel representations={[]} opportunities={[]} submissions={[]} />);
}

describe("RelationshipsPanel server state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listRelationships).mockResolvedValue([]);
    vi.mocked(getRelationshipAnalytics).mockResolvedValue(analytics);
    vi.mocked(listCommunicationLogs).mockResolvedValue([]);
  });

  it("shows loading, API error, and empty states", async () => {
    vi.mocked(listRelationships).mockReturnValueOnce(new Promise(() => undefined));
    const loading = renderPanel();
    expect(screen.getByRole("status")).toHaveTextContent("Loading Relationships");
    loading.unmount();

    vi.mocked(listRelationships).mockRejectedValueOnce(new ApiError({ message: "Relationships unavailable", status: 503 }));
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent("Relationships unavailable");
  });

  it("renders relationship and interaction records", async () => {
    vi.mocked(listRelationships).mockResolvedValue([relationship]);
    vi.mocked(listCommunicationLogs).mockResolvedValue([interaction]);
    renderPanel();
    expect(await screen.findByText("Morgan Lee")).toBeInTheDocument();
    expect(await screen.findByText("North Star follow-up")).toBeInTheDocument();
  });

  it("shows empty records and an independent interaction loading state", async () => {
    vi.mocked(listCommunicationLogs).mockReturnValue(new Promise(() => undefined));
    renderPanel();
    expect(await screen.findByText("No relationships tracked yet.")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Loading interaction history");
  });

  it("creates a relationship and invalidates records and analytics without reloading interactions", async () => {
    vi.mocked(createRelationship).mockResolvedValue(relationship);
    const { user } = renderPanel();
    const createForm = (await screen.findByRole("heading", { name: "Add Relationship" })).closest("form")!;
    await user.type(within(createForm).getByLabelText("Name"), "Morgan Lee");
    fireEvent.submit(createForm);
    await waitFor(() => expect(createRelationship).toHaveBeenCalledWith(expect.objectContaining({ name: "Morgan Lee" })));
    expect(listRelationships).toHaveBeenCalledTimes(2);
    expect(getRelationshipAnalytics).toHaveBeenCalledTimes(2);
    expect(listCommunicationLogs).toHaveBeenCalledTimes(1);
  });

  it("updates and deletes a relationship", async () => {
    vi.mocked(listRelationships).mockResolvedValue([relationship]);
    vi.mocked(updateRelationship).mockResolvedValue({ ...relationship, name: "Morgan Rivera" });
    vi.mocked(deleteRelationship).mockResolvedValue(undefined);
    const { user } = renderPanel();
    await user.click(await screen.findByRole("button", { name: "Edit" }));
    const editForm = screen.getByRole("heading", { name: "Save Relationship" }).closest("form")!;
    const name = within(editForm).getByLabelText("Name");
    await user.clear(name);
    await user.type(name, "Morgan Rivera");
    fireEvent.submit(editForm);
    await waitFor(() => expect(updateRelationship).toHaveBeenCalledWith("relationship-1", expect.objectContaining({ name: "Morgan Rivera" })));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(deleteRelationship).toHaveBeenCalledWith("relationship-1"));
  });

  it("adds and deletes interaction history with focused invalidation", async () => {
    vi.mocked(listCommunicationLogs).mockResolvedValue([interaction]);
    vi.mocked(createCommunicationLog).mockResolvedValue(interaction);
    vi.mocked(deleteCommunicationLog).mockResolvedValue(undefined);
    const { user } = renderPanel();
    const topic = await screen.findByLabelText("Topic");
    await user.type(topic, "North Star follow-up");
    fireEvent.submit(topic.closest("form")!);
    await waitFor(() => expect(createCommunicationLog).toHaveBeenCalledWith(expect.objectContaining({ topic: "North Star follow-up" })));
    expect(listCommunicationLogs).toHaveBeenCalledTimes(2);
    expect(listRelationships).toHaveBeenCalledTimes(1);
    const log = screen.getByText("North Star follow-up").closest("article")!;
    await user.click(within(log).getByRole("button", { name: "Delete" }));
    await user.click(within(log).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(deleteCommunicationLog).toHaveBeenCalledWith("log-1"));
  });
});
