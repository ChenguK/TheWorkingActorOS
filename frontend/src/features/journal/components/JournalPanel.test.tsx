import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../services/api/errors";
import { renderWithRouter, screen, waitFor } from "../../../test/testUtils";
import type { ActorJournalEntry } from "../../../types/domain";
import {
  createJournalEntry,
  deleteJournalEntry,
  listJournalEntries,
  updateJournalEntryNotes
} from "../api";
import { JournalPanel } from "./JournalPanel";

vi.mock("../api", () => ({
  createJournalEntry: vi.fn(),
  deleteJournalEntry: vi.fn(),
  listJournalEntries: vi.fn(),
  updateJournalEntryNotes: vi.fn()
}));

const entry: ActorJournalEntry = {
  id: "journal-1",
  date: "2026-07-16",
  event_type: "Audition",
  title: "Self-tape submitted",
  description: "Submitted before the deadline.",
  notes: "Used the dramatic take.",
  created_at: "2026-07-16T12:00:00Z",
  updated_at: "2026-07-16T12:00:00Z"
};

function renderPanel() {
  return renderWithRouter(
    <JournalPanel opportunities={[]} submissions={[]} assets={[]} careerTasks={[]} />
  );
}

describe("JournalPanel server state", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a loading state while Journal entries are fetched", () => {
    vi.mocked(listJournalEntries).mockReturnValue(new Promise(() => undefined));
    renderPanel();

    expect(screen.getByRole("status")).toHaveTextContent("Loading Journal entries");
  });

  it("shows meaningful Journal API errors", async () => {
    vi.mocked(listJournalEntries).mockRejectedValue(new ApiError({ message: "Journal service unavailable", status: 503 }));
    renderPanel();

    expect(await screen.findByRole("alert")).toHaveTextContent("Journal service unavailable");
  });

  it("renders the Journal entry list", async () => {
    vi.mocked(listJournalEntries).mockResolvedValue([entry]);
    renderPanel();

    expect(await screen.findByText("Self-tape submitted")).toBeInTheDocument();
    expect(screen.getByText("Used the dramatic take.")).toBeInTheDocument();
  });

  it("creates an entry through the Journal mutation without a workflow reload", async () => {
    vi.mocked(listJournalEntries).mockResolvedValue([]);
    vi.mocked(createJournalEntry).mockResolvedValue(entry);
    const { user } = renderPanel();

    await user.type(await screen.findByLabelText("Title"), "Self-tape submitted");
    await user.click(screen.getByRole("button", { name: "Save Entry" }));

    await waitFor(() => expect(createJournalEntry).toHaveBeenCalledWith(expect.objectContaining({ title: "Self-tape submitted" })));
    expect(await screen.findByText("Journal entry saved.")).toBeInTheDocument();
  });

  it("updates notes through the Journal mutation", async () => {
    vi.mocked(listJournalEntries).mockResolvedValue([entry]);
    vi.mocked(updateJournalEntryNotes).mockResolvedValue({ ...entry, notes: "Updated note" });
    const { user } = renderPanel();

    await user.click(await screen.findByRole("button", { name: "Edit notes" }));
    const notes = screen.getByRole("textbox");
    await user.clear(notes);
    await user.type(notes, "Updated note");
    await user.click(screen.getByRole("button", { name: "Save Notes" }));

    await waitFor(() => expect(updateJournalEntryNotes).toHaveBeenCalledWith("journal-1", "Updated note"));
    expect(await screen.findByText("Journal notes saved.")).toBeInTheDocument();
  });

  it("does not expose delete behavior until the existing UI supports it", () => {
    expect(deleteJournalEntry).not.toHaveBeenCalled();
  });
});
