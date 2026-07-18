import { describe, expect, it, vi } from "vitest";
import { ConfirmAction, ExpandableCard } from "./ui";
import { renderWithRouter, screen } from "../test/testUtils";

describe("shared UI primitives", () => {
  it("expands an ExpandableCard by click and keyboard", async () => {
    const { user } = renderWithRouter(
      <ExpandableCard title="Audition card" summary="Compact summary">
        <p>Expanded details</p>
      </ExpandableCard>
    );

    const toggle = screen.getByRole("button", { name: /audition card/i });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Expanded details")).not.toBeInTheDocument();

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("Expanded details")).toBeInTheDocument();

    await user.keyboard("{Enter}");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("requires confirmation before running a ConfirmAction", async () => {
    const onConfirm = vi.fn();
    const { user } = renderWithRouter(
      <ConfirmAction label="Delete" message="Delete this item?" confirmLabel="Yes, delete" onConfirm={onConfirm} />
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(screen.getByText("Delete this item?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onConfirm).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: /yes, delete/i }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
