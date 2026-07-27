import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../../../services/api/errors";
import { fireEvent, renderWithRouter, screen, waitFor } from "../../../test/testUtils";
import {
  analyzeMaterial,
  deleteMaterial,
  listMaterials,
  updateMaterial,
  uploadMaterial
} from "../api";
import type { ActorProfile, Asset } from "../types";
import { AssetLibrary } from "./AssetLibrary";

vi.mock("../api", () => ({
  analyzeMaterial: vi.fn(),
  assetFileUrl: (assetId: string) => `/assets/${assetId}/file`,
  deleteMaterial: vi.fn(),
  listMaterials: vi.fn(),
  updateMaterial: vi.fn(),
  uploadMaterial: vi.fn()
}));

function actorFixture(): ActorProfile {
  return {
    id: "actor-1", name: "Test Actor", sag_status: "SAG-AFTRA", union_status: "SAG-AFTRA",
    current_location: "Philadelphia, PA", playable_age_min: 25, playable_age_max: 40, skills: [],
    gender_identities: ["Woman"], ethnicities: ["Black"], racial_identities: ["Black"], nationalities: [],
    languages: ["English"], accents: [], disability_identities: [], included_role_types: [], excluded_role_types: [],
    created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z"
  };
}

function assetFixture(overrides: Partial<Asset> = {}): Asset {
  return {
    id: "asset-1", actor_profile_id: "actor-1", asset_name: "Warm Authority Headshot", asset_type: "Headshot",
    local_file_path: "/uploads/headshot.jpg", description: "Primary headshot", tags: ["warm"], archetype_names: ["Authority"],
    ai_suggested_tags: [], ai_suggested_archetypes: [], analysis_status: "Complete", freshness_status: "Current",
    created_at: "2026-07-01T00:00:00Z", updated_at: "2026-07-01T00:00:00Z", ...overrides
  };
}

describe("AssetLibrary server state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listMaterials).mockResolvedValue([]);
  });

  it("shows loading and API error states", async () => {
    vi.mocked(listMaterials).mockReturnValueOnce(new Promise(() => undefined));
    const loading = renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading Materials");
    loading.unmount();

    vi.mocked(listMaterials).mockRejectedValueOnce(new ApiError({ message: "Materials unavailable", status: 503 }));
    renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Materials unavailable");
  });

  it("renders material types from the authoritative list", async () => {
    vi.mocked(listMaterials).mockResolvedValue([
      assetFixture(),
      assetFixture({ id: "asset-2", asset_name: "Comedy Reel", asset_type: "Reel" })
    ]);
    renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    expect(await screen.findByText("Warm Authority Headshot")).toBeInTheDocument();
    expect(screen.getByText("Comedy Reel")).toBeInTheDocument();
    expect(screen.getByText("Headshot · Deterministic Recommendation")).toBeInTheDocument();
    expect(screen.getByText("Reel · Deterministic Recommendation")).toBeInTheDocument();
  });

  it("keeps upload disabled without a file and uploads authoritative FormData", async () => {
    vi.mocked(uploadMaterial).mockResolvedValue(assetFixture());
    const { user } = renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    await screen.findByRole("button", { name: "Upload" });
    expect(screen.getByRole("button", { name: "Upload" })).toBeDisabled();
    await user.type(screen.getByLabelText("Name"), "Warm Authority Headshot");
    const file = new File(["headshot"], "headshot.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText("File"), file);
    expect(screen.getByText("Selected file: headshot.jpg")).toBeInTheDocument();
    fireEvent.submit(screen.getByRole("button", { name: "Upload" }).closest("form")!);
    await waitFor(() => expect(uploadMaterial).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(uploadMaterial).mock.calls[0][0];
    expect(payload.get("actor_profile_id")).toBe("actor-1");
    expect(payload.get("asset_type")).toBe("Headshot");
    expect(payload.get("file")).toBe(file);
    expect(await screen.findByText(/was uploaded to Materials/)).toBeInTheDocument();
    expect(listMaterials).toHaveBeenCalledTimes(2);
  });

  it("keeps hosted demo materials readable without exposing file mutations", async () => {
    vi.mocked(listMaterials).mockResolvedValue([assetFixture()]);
    renderWithRouter(
      <AssetLibrary
        actor={actorFixture()}
        capabilities={{
          flags: {
            ai_configured: false,
            persistent_file_storage_available: false
          }
        } as never}
      />
    );

    expect(await screen.findByText("Warm Authority Headshot")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload Material" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByText(/File uploads are disabled in the hosted demo/)).toBeInTheDocument();
    expect(uploadMaterial).not.toHaveBeenCalled();
  });

  it("preserves upload controls when persistent storage is available", async () => {
    renderWithRouter(
      <AssetLibrary
        actor={actorFixture()}
        capabilities={{
          flags: {
            ai_configured: false,
            persistent_file_storage_available: true
          }
        } as never}
      />
    );

    expect(await screen.findByRole("button", { name: "Upload" })).toBeInTheDocument();
    expect(screen.getByLabelText("File")).toBeInTheDocument();
    expect(screen.queryByText(/File uploads are disabled/)).not.toBeInTheDocument();
  });

  it("preserves an upload draft and backend message after API failure", async () => {
    vi.mocked(uploadMaterial).mockRejectedValue(new ApiError({ message: "Unsupported upload", status: 422 }));
    const { user } = renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    const name = await screen.findByLabelText("Name");
    await user.type(name, "Keep this material");
    await user.upload(screen.getByLabelText("File"), new File(["x"], "asset.bin"));
    fireEvent.submit(screen.getByRole("button", { name: "Upload" }).closest("form")!);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unsupported upload");
    expect(name).toHaveValue("Keep this material");
  });

  it("edits and deletes through focused Materials mutations without a workflow refresh", async () => {
    const asset = assetFixture();
    vi.mocked(listMaterials).mockResolvedValue([asset]);
    vi.mocked(updateMaterial).mockResolvedValue({ ...asset, asset_name: "Updated Headshot" });
    vi.mocked(deleteMaterial).mockResolvedValue(undefined);
    const promptSpy = vi.spyOn(window, "prompt");
    const { user } = renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    await user.click(await screen.findByRole("button", { name: "Edit" }));
    const name = screen.getByLabelText("Material Name");
    await user.clear(name);
    await user.type(name, "Updated Headshot");
    await user.click(screen.getByRole("button", { name: "Save Material" }));
    await waitFor(() => expect(updateMaterial).toHaveBeenCalledWith("asset-1", expect.objectContaining({ asset_name: "Updated Headshot" })));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Delete", hidden: true }));
    await waitFor(() => expect(deleteMaterial).toHaveBeenCalledWith("asset-1"));
    expect(promptSpy).not.toHaveBeenCalled();
  });

  it("analyzes through the Materials API and invalidates only the Materials list", async () => {
    vi.mocked(listMaterials).mockResolvedValue([assetFixture()]);
    vi.mocked(analyzeMaterial).mockResolvedValue(undefined);
    const { user } = renderWithRouter(<AssetLibrary actor={actorFixture()} />);
    await user.click(await screen.findByRole("button", { name: "Analyze" }));
    await waitFor(() => expect(analyzeMaterial).toHaveBeenCalledWith("asset-1"));
    expect(listMaterials).toHaveBeenCalledTimes(2);
  });
});
