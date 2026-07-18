import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithRouter } from "../../../test/testUtils";
import * as api from "../api";
import type { Opportunity } from "../types";
import { OpportunityFormWorkspace, type OpportunityFormMode } from "./OpportunityFormWorkspace";

vi.mock("../api", () => ({ createBreakdown: vi.fn(async () => ({})), updateBreakdown: vi.fn(async () => ({})) }));

const record = (id: string, role: string) => ({
  id, role, project: "Pilot", description: `${role} description`, source_type: "Manual Entry", from_agent: false,
  representation_id: null, platform: null, project_type: null, role_type: null, union: "SAG-AFTRA", rate: null,
  location: "New York", shoot_location: null, audition_location: null, travel_covered: null, housing_covered: null,
  audition_type: "Virtual", audition_travel_hours: null, original_post_url: null, audition_deadline: null,
  submission_deadline: null, callback_date: null, shoot_start_date: null, shoot_end_date: null, priority: "Medium",
  archetypes: [], source_metadata: {}, production_details: {}, role_details: {}
} as unknown as Opportunity);

function Harness({ initial, opportunities }: { initial: OpportunityFormMode; opportunities: Opportunity[] }) {
  const [mode, setMode] = useState(initial);
  return <><OpportunityFormWorkspace mode={mode} onModeChange={setMode} opportunities={opportunities} representations={[]} /><output data-testid="mode">{mode.kind}</output></>;
}

describe("OpportunityFormWorkspace", () => {
  it("renders nothing when closed and closes a clean create on cancel", async () => {
    const closed = renderWithRouter(<Harness initial={{ kind: "closed" }} opportunities={[]} />);
    expect(screen.queryByRole("heading", { name: "Add Breakdown" })).not.toBeInTheDocument();
    closed.unmount();
    const view = renderWithRouter(<Harness initial={{ kind: "create" }} opportunities={[]} />);
    await view.user.type(screen.getByLabelText("Role"), "Draft"); await view.user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByTestId("mode")).toHaveTextContent("closed");
  });

  it("keeps a complete create draft open and announces API failure without invalidating success", async () => {
    vi.mocked(api.createBreakdown).mockRejectedValueOnce(new Error("Create unavailable"));
    const view = renderWithRouter(<Harness initial={{ kind: "create" }} opportunities={[]} />);
    for (const [label, value] of [["Role", "Neighbor"], ["Project", "Pilot"], ["Shoot Location", "New York"], ["Character Breakdown", "Comedy role"]]) {
      await view.user.type(screen.getByLabelText(label), value);
    }
    await view.user.click(screen.getByRole("button", { name: "Create Breakdown" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Create unavailable");
    expect(screen.getByLabelText("Role")).toHaveValue("Neighbor");
    expect(screen.getByLabelText("Character Breakdown")).toHaveValue("Comedy role");
    expect(screen.getByTestId("mode")).toHaveTextContent("create");
  });

  it("refreshes an authoritative edit before dirty and preserves it after dirty", async () => {
    function RefreshHarness() {
      const [items, setItems] = useState([record("o1", "First")]);
      return <><OpportunityFormWorkspace mode={{ kind: "edit", opportunityId: "o1" }} onModeChange={() => undefined} opportunities={items} representations={[]} /><button onClick={() => setItems([record("o1", "Refreshed")])}>Refresh</button></>;
    }
    const view = renderWithRouter(<RefreshHarness />);
    expect(screen.getByLabelText("Role")).toHaveValue("First");
    await view.user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(screen.getByLabelText("Role")).toHaveValue("Refreshed");
    await view.user.clear(screen.getByLabelText("Role")); await view.user.type(screen.getByLabelText("Role"), "Dirty");
    await view.user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(screen.getByLabelText("Role")).toHaveValue("Dirty");
  });

  it("switches edit IDs without leaking drafts and closes when the record disappears", async () => {
    function SwitchHarness() {
      const [mode, setMode] = useState<OpportunityFormMode>({ kind: "edit", opportunityId: "o1" });
      const [items, setItems] = useState([record("o1", "First"), record("o2", "Second")]);
      return <><OpportunityFormWorkspace mode={mode} onModeChange={setMode} opportunities={items} representations={[]} /><button onClick={() => setMode({ kind: "edit", opportunityId: "o2" })}>Second</button><button onClick={() => setItems([])}>Remove</button><output data-testid="mode">{mode.kind}</output></>;
    }
    const view = renderWithRouter(<SwitchHarness />);
    await view.user.clear(screen.getByLabelText("Role")); await view.user.type(screen.getByLabelText("Role"), "Dirty first");
    await view.user.click(screen.getByRole("button", { name: "Second" }));
    expect(screen.getByLabelText("Role")).toHaveValue("Second");
    await view.user.click(screen.getByRole("button", { name: "Remove" }));
    await waitFor(() => expect(screen.getByTestId("mode")).toHaveTextContent("closed"));
  });
});
