import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CommandCenterCard, OpportunityIntelligenceSummary } from "../../../types/domain";
import { OpportunityPriorityCard } from "./DashboardPanel";

const summary: OpportunityIntelligenceSummary = {
  version: 1,
  overall_score: 87,
  action: "apply_now",
  action_label: "Apply Now",
  action_reason_code: "high_priority_actionable",
  confidence: {
    level: "High",
    summary: "This recommendation is supported by strong information."
  },
  hard_override: false,
  hard_override_reason: null,
  top_positive_contributors: [
    { id: "match.role_fit.strong", points: 18, explanation: "The strongest parsed role is a strong fit." }
  ],
  top_negative_contributors: [
    { id: "confidence.completeness.incomplete", points: -4 }
  ]
};

function card(intelligence?: CommandCenterCard["intelligence"]): CommandCenterCard {
  return {
    id: "card-1",
    role: "Detective",
    project: "Fictional Procedural",
    ...(intelligence === undefined ? {} : { intelligence })
  };
}

describe("OpportunityPriorityCard", () => {
  it.each([undefined, null, { version: 2 }])(
    "preserves the legacy card for unavailable or unsupported intelligence %#",
    (intelligence) => {
      render(<OpportunityPriorityCard opportunity={card(intelligence)} />);

      expect(screen.getByText("Detective")).toBeInTheDocument();
      expect(screen.getByText("Fictional Procedural")).toBeInTheDocument();
      expect(screen.queryByText(/Score/)).not.toBeInTheDocument();
    }
  );

  it("renders visible, screen-reader, and keyboard-operable intelligence details", () => {
    render(<OpportunityPriorityCard opportunity={card(summary)} />);

    expect(screen.getByText("Detective")).toBeInTheDocument();
    expect(screen.getByText("Fictional Procedural")).toBeInTheDocument();
    expect(screen.getByText("Apply Now")).toBeVisible();
    expect(screen.getByText("Score 87 of 100 · High confidence")).toBeVisible();
    expect(screen.getByLabelText("Opportunity intelligence: Apply Now; score 87 of 100")).toBeVisible();
    const disclosure = screen.getByText("Why this score");
    expect(disclosure.closest("details")).not.toHaveAttribute("open");
    fireEvent.click(disclosure);
    expect(disclosure.closest("details")).toHaveAttribute("open");
    expect(screen.getByText(/Positive: The strongest parsed role/)).toBeVisible();
    expect(screen.getByText(/Negative: confidence.completeness.incomplete/)).toBeVisible();
  });

  it("distinguishes evaluated neutral and bounded hard-override summaries", () => {
    const { rerender } = render(
      <OpportunityPriorityCard opportunity={card({
        ...summary,
        overall_score: 50,
        action: "low_priority",
        action_label: "Low Priority",
        confidence: { level: "Not Scored", summary: "Neutral." },
        top_positive_contributors: [],
        top_negative_contributors: []
      })} />
    );
    expect(screen.getByText("Score 50 of 100 · Not Scored confidence")).toBeVisible();
    expect(screen.queryByText("Why this score")).not.toBeInTheDocument();

    rerender(<OpportunityPriorityCard opportunity={card({
      ...summary,
      overall_score: 0,
      action: "ignore",
      action_label: "Ignore",
      hard_override: true,
      hard_override_reason: "profile_incompatibility"
    })} />);
    expect(screen.getByText("Ignore")).toBeVisible();
    expect(screen.getByText("Reason: profile incompatibility")).toBeVisible();
  });

  it("falls back to the legacy card for an invalid runtime score", () => {
    render(<OpportunityPriorityCard opportunity={card({ ...summary, overall_score: 101 })} />);

    expect(screen.getByText("Detective")).toBeVisible();
    expect(screen.queryByText(/Score 101/)).not.toBeInTheDocument();
  });
});
