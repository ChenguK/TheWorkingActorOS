import { render, screen, waitFor } from "@testing-library/react";
import { renderWithRouter } from "../../../test/testUtils";
import { describe, expect, it, vi } from "vitest";
import { CapabilityStatusPanel } from "./CapabilityStatusPanel";
import { DiscoveryProviderSettingsPanel } from "./DiscoveryProviderSettingsPanel";
import { IntegrationsStatusPanel } from "./IntegrationsStatusPanel";
import { SettingsPanel } from "./SettingsPanel";
import { getSystemCapabilities } from "../../../services/system";
import type { DiscoveryProviderSettings, SystemCapabilities } from "../types";

vi.mock("../api", () => ({
  healthCheckDiscoveryProvider: vi.fn(),
  listDiscoveryProviders: vi.fn(),
  recalculateTravelExceptions: vi.fn(),
  updateDiscoveryProvider: vi.fn()
}));

vi.mock("../../../services/system/api", () => ({ getSystemCapabilities: vi.fn() }));

const capabilities: SystemCapabilities = {
  flags: {
    travel_provider_configured: true,
    ai_configured: false,
    scheduler_configured: false,
    notifications_configured: false,
    source_discovery_configured: true,
    public_profile_import_configured: true,
    supervised_browser_available: false,
    persistent_file_storage_available: false,
    portfolio_demo: true
  },
  states: {
    drive_time_calculation: {
      state: "Configured",
      explanation: "OpenRouteService is configured for drive-time estimates.",
      safe_fallback: "Manual drive-time estimate"
    },
    notification_reminders: {
      state: "Dashboard Alerts Only",
      explanation: "Notification delivery is not configured.",
      safe_fallback: "Dashboard alerts only"
    }
  },
  integrations: [
    {
      id: "openrouteservice",
      name: "OpenRouteService API",
      status: "Configured",
      configured: true,
      what_it_enables: "Drive-time calculation",
      fallback_behavior: "Manual drive-time estimate",
      setup_instructions: "Set OPENROUTESERVICE_API_KEY on the backend.",
      provider: "openrouteservice"
    },
    {
      id: "openai",
      name: "OpenAI API",
      status: "Not Configured",
      configured: false,
      what_it_enables: "AI-assisted parsing and tagging",
      fallback_behavior: "Deterministic suggestions",
      setup_instructions: "Set OPENAI_API_KEY on the backend."
    },
    {
      id: "supervised_browser",
      name: "Supervised Browser Import",
      status: "Unavailable in Portfolio Demo",
      configured: false,
      what_it_enables: "A user-controlled local browser",
      fallback_behavior: "Manual breakdown entry or pasted breakdown text.",
      setup_instructions: "Available only in local development."
    }
  ],
  labels: {
    not_configured: "Not Configured",
    needs_info: "Needs Info",
    manual_override: "Manual Override",
    user_entered_estimate: "User-entered estimate",
    add_data_first: "Add Data First",
    insufficient_data: "Insufficient Data",
    dashboard_alerts_only: "Dashboard Alerts Only",
    manual_check_in: "Manual Check-In",
    suggested_tags: "Suggested Tags",
    deterministic_recommendation: "Deterministic Recommendation"
  }
};

const provider: DiscoveryProviderSettings = {
  id: "provider-1",
  provider_key: "public-web",
  display_name: "Public Web Search",
  category: "Public Casting Sites",
  source_type: "Breakdown Source",
  tier: 2,
  enabled: true,
  poll_frequency_minutes: 1440,
  priority: 10,
  authentication_method: "None",
  supported_authentication_methods: ["None"],
  reliability_score: 0.9,
  health_status: "Healthy",
  health_message: null,
  last_health_check_at: null,
  notes: "Technical provider only.",
  provider_metadata: {},
  created_at: "2026-01-01",
  updated_at: "2026-01-01"
};

describe("Settings feature", () => {
  it("shows configured and not configured integration status with fallback text", () => {
    render(<IntegrationsStatusPanel capabilities={capabilities} />);

    expect(screen.getByText("OpenRouteService API")).toBeInTheDocument();
    expect(screen.getByText("OpenAI API")).toBeInTheDocument();
    expect(screen.getByText("Drive-time calculation")).toBeInTheDocument();
    expect(screen.getByText("Deterministic suggestions")).toBeInTheDocument();
    expect(screen.getByText("Supervised Browser Import")).toBeInTheDocument();
    expect(screen.getByText("Manual breakdown entry or pasted breakdown text.")).toBeInTheDocument();
    expect(screen.getByText("Not Configured")).toBeInTheDocument();
  });

  it("does not display secret values in integration setup text", () => {
    render(<IntegrationsStatusPanel capabilities={capabilities} />);

    expect(screen.queryByText(/sk-/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/OPENROUTESERVICE_API_KEY=.*\w/i)).not.toBeInTheDocument();
    expect(screen.getByText(/API keys are read from backend environment variables only/i)).toBeInTheDocument();
  });

  it("shows capability flags without duplicating actor travel preference controls", async () => {
    vi.mocked(getSystemCapabilities).mockResolvedValue(capabilities);
    renderWithRouter(<CapabilityStatusPanel />);

    expect(await screen.findByText("Travel Configured")).toBeInTheDocument();
    expect(screen.getByText("Deterministic Recommendation")).toBeInTheDocument();
    expect(screen.getAllByText("Dashboard Alerts Only").length).toBeGreaterThan(0);
    expect(screen.queryByText("Audition Travel Preferences")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Audition Max Drive Time")).not.toBeInTheDocument();
  });

  it("shows provider technical settings without Source Library approval controls", async () => {
    const api = await import("../api");
    vi.mocked(api.listDiscoveryProviders).mockResolvedValue([provider]);
    renderWithRouter(<DiscoveryProviderSettingsPanel />);

    await waitFor(() => expect(screen.getByText("Public Web Search")).toBeInTheDocument());

    expect(screen.getByText("Breakdown Source · priority 10")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Health Check" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
  });

  it("does not show editable actor subscription setup in Settings", async () => {
    const api = await import("../api");
    vi.mocked(api.listDiscoveryProviders).mockResolvedValue([provider]);
    vi.mocked(getSystemCapabilities).mockResolvedValue(capabilities);
    renderWithRouter(<SettingsPanel />);

    await waitFor(() => expect(screen.getByText("Public Web Search")).toBeInTheDocument());
    expect(screen.queryByText("Casting Platform Subscriptions")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Subscription Level")).not.toBeInTheDocument();
  });
});
