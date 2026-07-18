import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithRouter } from "../../../test/testUtils";
import { ActingResumeBuilder } from "./ActingResumeBuilder";
import { ActorProfilePanel } from "./ActorProfilePanel";
import { PlatformProfileImportAssistant } from "./PlatformProfileImportAssistant";
import { ProfessionalCapabilitiesPanel } from "./ProfessionalCapabilitiesPanel";
import { ProfileSubscriptionsPanel } from "./ProfileSubscriptionsPanel";
import { ProfileSetupPanel } from "./ProfileSetupPanel";
import { TravelPreferencePanel } from "./TravelPreferencePanel";
import type { ActorProfile } from "../../../types/domain";

vi.mock("../api", () => ({
  getActorProfile: vi.fn(), getProfessionalEquipmentProfile: vi.fn(), getTravelPreferences: vi.fn(), listActingCredits: vi.fn(),
  listPlatformAssetMappings: vi.fn(), listPlatformProfiles: vi.fn(), listPlatformSubscriptions: vi.fn(), listPublicProfileImports: vi.fn(), listRepresentations: vi.fn(),
  updateActorProfile: vi.fn(), saveTravelPreferences: vi.fn(), createRepresentation: vi.fn(), updateRepresentation: vi.fn(), deleteRepresentation: vi.fn(),
  createActingCredit: vi.fn(), updateActingCredit: vi.fn(), deleteActingCredit: vi.fn(), importPublicProfileUrl: vi.fn(), importProfileUpload: vi.fn(),
  approvePublicProfileImport: vi.fn(), rejectPublicProfileImport: vi.fn(), deletePublicProfileImport: vi.fn(), approvePlatformProfileImport: vi.fn(),
  rejectPlatformProfileImport: vi.fn(), deletePlatformProfileImport: vi.fn(), createPlatformAssetMapping: vi.fn(), updatePlatformAssetMapping: vi.fn(),
  deletePlatformAssetMapping: vi.fn(), updatePlatformSubscription: vi.fn(), updateProfessionalEquipmentProfile: vi.fn(),
  generatedResumePdfUrl: vi.fn(() => "#pdf"), generatedResumeDocxUrl: vi.fn(() => "#docx")
}));
vi.mock("../../materials", async () => ({ useMaterialOptions: () => ({ data: [], isLoading: false, isRefetching: false }) }));
import * as profileApi from "../api";

const actor: ActorProfile = {
  id: "actor-1",
  name: "Chengu",
  sag_status: "SAG-AFTRA",
  union_status: "SAG-AFTRA",
  current_location: "Philadelphia, PA",
  playable_age_min: 25,
  playable_age_max: 35,
  secondary_playable_age_min: null,
  secondary_playable_age_max: null,
  skills: ["Comedy"],
  gender_identities: ["Woman"],
  gender_expression: "Female Presenting",
  pronouns: "she/her",
  ethnicities: ["African American"],
  racial_identities: ["Black"],
  nationalities: ["American"],
  languages: ["English"],
  accents: ["American"],
  disability_identities: [],
  included_role_types: ["Lead"],
  excluded_role_types: ["Background"],
  accessibility_notes: null,
  demographic_notes: null,
  notes: null,
  created_at: "2026-01-01",
  updated_at: "2026-01-01"
};

describe("Profile feature", () => {
  beforeEach(() => {
    vi.mocked(profileApi.getActorProfile).mockResolvedValue(actor);
    vi.mocked(profileApi.getTravelPreferences).mockResolvedValue(null);
    vi.mocked(profileApi.listRepresentations).mockResolvedValue([]);
    vi.mocked(profileApi.listActingCredits).mockResolvedValue([]);
    vi.mocked(profileApi.listPlatformProfiles).mockResolvedValue([]);
    vi.mocked(profileApi.listPublicProfileImports).mockResolvedValue([]);
  });

  it("shows Profile setup completion status from actor data", async () => {
    renderWithRouter(<ProfileSetupPanel />);

    expect(screen.getByText("Profile Setup")).toBeInTheDocument();
    expect(await screen.findByText(/3\s+of\s+8\s+steps complete/)).toBeInTheDocument();
    expect(screen.getByText("1. Basic Info")).toBeInTheDocument();
  });

  it("keeps profile import draft submission disabled until file or text is provided", async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <PlatformProfileImportAssistant
        actor={null}
        assets={[]}
        profiles={[]}
        publicImports={[]}
        mappings={[]}
      />
    );

    const createButton = screen.getByRole("button", { name: "Create Draft Import" });
    expect(createButton).toBeDisabled();

    await user.type(screen.getByLabelText("Profile Text / Guided Form Answers"), "Television credit, comedy skills");

    expect(createButton).toBeEnabled();
  });

  it("shows professional identity, demographics, languages, role preferences, and representation from saved Profile data", () => {
    renderWithRouter(
      <ActorProfilePanel
        actor={actor}
        representations={[
          {
            id: "rep-1",
            actor_profile_id: actor.id,
            agency_name: "Example Agency",
            agent_name: "Example Agent",
            agent_email: "agent@example.com",
            agent_phone: "555-0100",
            agency_website: "https://example.com",
            representation_type: "Theatrical",
            market: ["Philadelphia"],
            notes: "Theatrical rep.",
            active: true,
            start_date: "2026-01-01",
            end_date: null,
            created_at: "2026-01-01",
            updated_at: "2026-01-01"
          }
        ]}
      />
    );

    expect(screen.getByText("Saved Profile")).toBeInTheDocument();
    expect(screen.getByText("Chengu")).toBeInTheDocument();
    expect(screen.getByText("African American")).toBeInTheDocument();
    expect(screen.getByText("Black")).toBeInTheDocument();
    expect(screen.getByText("English")).toBeInTheDocument();
    expect(screen.getByText("Lead")).toBeInTheDocument();
    expect(screen.getByText("Represented by Example Agency")).toBeInTheDocument();
  });

  it("shows travel preferences in plain English with separate audition and working travel sections", () => {
    renderWithRouter(
      <TravelPreferencePanel
        actor={actor}
        travel={{
          id: "travel-1",
          actor_profile_id: actor.id,
          max_local_drive_time: 300,
          extended_drive_time: 720,
          flight_allowed: true,
          housing_required: true,
          international_allowed: false,
          audition_max_drive_time: 120,
          audition_virtual_allowed: true,
          audition_self_tape_allowed: true,
          working_as_local_drive_time: 180,
          working_as_local_housing_self_provided: true,
          require_travel_housing_over_local_drive: true,
          audition_notes: "Prefer self-tapes.",
          working_notes: "Need clear terms.",
          created_at: "2026-01-01",
          updated_at: "2026-01-01"
        }}
      />
    );

    expect(screen.getByText("Plain-English Summary")).toBeInTheDocument();
    expect(screen.getByText("Audition Travel")).toBeInTheDocument();
    expect(screen.getByText("Working as Local")).toBeInTheDocument();
    expect(screen.getByText("Production Travel If Covered")).toBeInTheDocument();
  });

  it("edits platform mapping notes with an inline form instead of a browser prompt", async () => {
    const user = userEvent.setup();
    const promptSpy = vi.spyOn(window, "prompt");
    renderWithRouter(
      <PlatformProfileImportAssistant
        actor={null}
        assets={[]}
        profiles={[]}
        publicImports={[]}
        mappings={[
          {
            id: "mapping-1",
            platform_name: "Actors Access",
            platform_asset_name: "Commercial Headshot",
            asset_type: "Headshot",
            local_asset_id: null,
            tags: ["commercial"],
            archetypes: ["Warm"],
            notes: "Use for commercial roles.",
            created_at: "2026-01-01",
            updated_at: "2026-01-01"
          }
        ]}
      />
    );

    await user.click(screen.getByRole("button", { name: "Edit Notes" }));

    expect(promptSpy).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Mapping Notes")).toHaveValue("Use for commercial roles.");
    expect(screen.getByRole("button", { name: "Save Notes" })).toBeInTheDocument();

    promptSpy.mockRestore();
  });

  it("shows professional capabilities under Profile without availability scheduling", () => {
    renderWithRouter(
      <ProfessionalCapabilitiesPanel
        actor={null}
        equipmentProfile={{
          id: "equipment-1",
          actor_profile_id: null,
          cameras: ["iPhone"],
          lighting: ["Softbox"],
          audio_equipment: ["Lav mic"],
          backdrops: ["Blue"],
          editing_software: ["Final Cut"],
          teleprompter: true,
          reader_availability: "Available evenings",
          internet_upload_speed: "Fast",
          home_audition_space: "Quiet room",
          notes: "Good self-tape setup.",
          created_at: "2026-01-01",
          updated_at: "2026-01-01"
        }}
      />
    );

    expect(screen.getAllByText("Professional Materials & Equipment Profile").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Cameras")).toHaveValue("iPhone");
    expect(screen.queryByText("Add Availability Block")).not.toBeInTheDocument();
  });

  it("shows platform subscription setup under Profile", () => {
    renderWithRouter(
      <ProfileSubscriptionsPanel
        subscriptions={[
          {
            id: "sub-1",
            platform_name: "Actors Access",
            has_subscription: true,
            subscription_level: "Plus",
            monthly_cost: 9.99,
            annual_cost: null,
            renewal_date: "2026-12-31",
            notes: "Primary platform.",
            active: true,
            created_at: "2026-01-01",
            updated_at: "2026-01-01"
          }
        ]}
      />
    );

    expect(screen.getByText("Casting Platform Subscriptions")).toBeInTheDocument();
    expect(screen.getByText("Actors Access")).toBeInTheDocument();
    expect(screen.getByLabelText("Subscription Level")).toHaveValue("Plus");
    expect(screen.getByLabelText("Monthly Cost")).toHaveValue(9.99);
  });

  it("keeps theater and training resume columns in the casting-profile preview", () => {
    renderWithRouter(
      <ActingResumeBuilder
        actor={actor}
        credits={[
          {
            id: "credit-1",
            actor_profile_id: actor.id,
            category: "Theater",
            section_enabled: true,
            section_order: 0,
            display_order: 0,
            highlighted: false,
            project_title: "A Play",
            role_or_character: "Lead",
            role_type: null,
            production_company: "Example Theater",
            network_or_distributor: null,
            director: "Example Director",
            episode_title: null,
            season_episode: null,
            year: "2026",
            union_status: null,
            class_or_program: null,
            instructor: null,
            institution: null,
            skill_name: null,
            skill_category: null,
            proficiency: null,
            notes: null,
            created_at: "2026-01-01",
            updated_at: "2026-01-01"
          },
          {
            id: "credit-2",
            actor_profile_id: actor.id,
            category: "Training",
            section_enabled: true,
            section_order: 1,
            display_order: 0,
            highlighted: false,
            project_title: null,
            role_or_character: null,
            role_type: null,
            production_company: null,
            network_or_distributor: null,
            director: null,
            episode_title: null,
            season_episode: null,
            year: "2025",
            union_status: null,
            class_or_program: "Scene Study",
            instructor: "Example Teacher",
            institution: "Example Studio",
            skill_name: null,
            skill_category: null,
            proficiency: null,
            notes: null,
            created_at: "2026-01-01",
            updated_at: "2026-01-01"
          }
        ]}
      />
    );

    expect(screen.getByText("Casting-Profile Preview")).toBeInTheDocument();
    expect(screen.getAllByText("Theater").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Project Name").length).toBeGreaterThan(0);
    expect(screen.getByText("Example Theater")).toBeInTheDocument();
    expect(screen.getAllByText("Training").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Teacher").length).toBeGreaterThan(0);
    expect(screen.getByText("Example Teacher")).toBeInTheDocument();
  });
});
