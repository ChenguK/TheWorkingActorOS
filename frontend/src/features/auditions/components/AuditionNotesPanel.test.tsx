import { describe, expect, it, vi } from "vitest";
import { AuditionNotesPanel } from "./AuditionNotesPanel";
import { updateAuditionNote } from "../api";
import { renderWithRouter, screen } from "../../../test/testUtils";
import type { AuditionJournalEntry } from "../types";

vi.mock("../api", () => ({
  createAuditionNote: vi.fn(),
  deleteAuditionNote: vi.fn(),
  updateAuditionNote: vi.fn()
}));

function journalEntryFixture(): AuditionJournalEntry {
  return {
    id: "note-1",
    submission_id: null,
    opportunity_id: null,
    date: "2026-07-10",
    preparation_notes: "Review sides",
    performance_notes: "Original performance",
    casting_notes: null,
    wardrobe_notes: "Blue blazer",
    emotional_notes: null,
    follow_up_notes: null,
    created_at: "2026-07-10T00:00:00Z",
    updated_at: "2026-07-10T00:00:00Z"
  };
}

describe("AuditionNotesPanel", () => {
  it("opens the Edit Performance form and cancel does not save", async () => {
    const promptSpy = vi.spyOn(window, "prompt");
    const { user } = renderWithRouter(
      <AuditionNotesPanel journalEntries={[journalEntryFixture()]} opportunities={[]} submissions={[]} />
    );

    await user.click(screen.getByRole("button", { name: "Edit Performance" }));

    expect(promptSpy).not.toHaveBeenCalled();
    expect(screen.getByDisplayValue("Original performance")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(updateAuditionNote).not.toHaveBeenCalled();
  });
});
