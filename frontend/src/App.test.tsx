import { describe, expect, it, vi } from "vitest";
import App from "./App";
import { renderWithRouter, screen } from "./test/testUtils";

vi.mock("./pages/DashboardPage", () => ({ DashboardPage: () => <div>Dashboard route loaded</div> }));
vi.mock("./pages/AuditionsPage", () => ({ AuditionsPage: () => <div>Auditions route loaded</div> }));
vi.mock("./pages/OpportunitiesPage", () => ({ OpportunitiesPage: () => <div>Breakdowns route loaded</div> }));
vi.mock("./pages/MaterialsPage", () => ({ MaterialsPage: () => <div>Materials route loaded</div> }));
vi.mock("./pages/CareerPage", () => ({ CareerPage: () => <div>Career route loaded</div> }));
vi.mock("./pages/AnalyticsPage", () => ({ AnalyticsPage: () => <div>Analytics route loaded</div> }));
vi.mock("./pages/RelationshipsPage", () => ({ RelationshipsPage: () => <div>Relationships route loaded</div> }));
vi.mock("./pages/CalendarPage", () => ({ CalendarPage: () => <div>Calendar route loaded</div> }));
vi.mock("./pages/JournalPage", () => ({ JournalPage: () => <div>Journal route loaded</div> }));
vi.mock("./pages/ProfilePage", () => ({ ProfilePage: () => <div>Profile route loaded</div> }));
vi.mock("./pages/ProfileSetupPage", () => ({ ProfileSetupPage: () => <div>Profile setup route loaded</div> }));
vi.mock("./pages/SettingsPage", () => ({ SettingsPage: () => <div>Settings route loaded</div> }));

describe("lazy app routes", () => {
  it("loads a lazy route after the route-level loading state", async () => {
    renderWithRouter(<App />, { route: "/materials" });

    expect(screen.getByRole("status")).toHaveTextContent(/loading workspace section/i);
    expect(await screen.findByText("Materials route loaded")).toBeInTheDocument();
  });

  it("keeps navigation usable without a global workflow loading gate or refresh control", async () => {
    renderWithRouter(<App />);
    expect(screen.getByRole("navigation", { name: /primary workflow navigation/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^refresh$/i })).not.toBeInTheDocument();
    expect(await screen.findByText("Dashboard route loaded")).toBeInTheDocument();
  });
});
