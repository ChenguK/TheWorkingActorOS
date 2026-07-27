import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Briefcase, Clapperboard, Download, Edit3, Eye, EyeOff, MapPin, Save, Star, Trash2, UserRound, X } from "lucide-react";
import { Badge, Button, CapabilityNotice, EmptyState, Field, Section, StatusBadge, inputClass } from "../../../components/ui";
import { formatDateTime } from "../../../utils/dateTime";
import { joinList, splitList } from "../../../utils/tags";
import type {
  ActingCredit,
  ActingCreditCategory,
  ActorProfile,
  AssetType,
  CastingPlatformSubscription,
  PlatformAssetMapping,
  PlatformImportMethod,
  PlatformName,
  PlatformProfile,
  ProfessionalEquipmentProfile,
  PublicProfileImport,
  Representation,
  SystemCapabilities,
  TravelPreference
} from "../../../types/domain";
import type { MaterialOption } from "../../materials";
import { assetTypes } from "../../../constants/workflowOptions";
import { useCreatePlatformMapping, useDeletePlatformMapping, useImportProfileUpload, useImportPublicProfile, usePlatformImportAction, usePublicImportAction, useUpdatePlatformMapping } from "../hooks/useProfileQueries";
import { platformImportMethods, platformNames } from "./ProfileFormShared";

export function PlatformProfileImportAssistant({
  actor,
  assets,
  profiles,
  publicImports,
  mappings,
  capabilities
}: {
  actor: ActorProfile | null;
  assets: MaterialOption[];
  profiles: PlatformProfile[];
  publicImports: PublicProfileImport[];
  mappings: PlatformAssetMapping[];
  capabilities?: SystemCapabilities | null;
}) {
  const persistentStorageAvailable = capabilities?.flags.persistent_file_storage_available ?? true;
  const publicImportMutation = useImportPublicProfile();
  const uploadMutation = useImportProfileUpload();
  const publicActionMutation = usePublicImportAction();
  const platformActionMutation = usePlatformImportAction();
  const createMappingMutation = useCreatePlatformMapping();
  const updateMappingMutation = useUpdatePlatformMapping();
  const deleteMappingMutation = useDeletePlatformMapping();
  const [draftFile, setDraftFile] = useState<File | null>(null);
  const [draftFileInputKey, setDraftFileInputKey] = useState(0);
  const [draftImportSaving, setDraftImportSaving] = useState(false);
  const [draftImportMessage, setDraftImportMessage] = useState<string | null>(null);
  const [draftImportError, setDraftImportError] = useState<string | null>(null);
  const [publicForm, setPublicForm] = useState({
    platform_name: "Casting Networks" as PlatformName,
    profile_url: ""
  });
  const [draftForm, setDraftForm] = useState({
    platform_name: "Actors Access" as PlatformName,
    profile_url: "",
    import_method: "Manual Copy/Paste" as PlatformImportMethod,
    raw_import_text: ""
  });
  const [mappingForm, setMappingForm] = useState({
    platform_name: "Actors Access" as PlatformName,
    platform_asset_name: "",
    asset_type: "Headshot" as AssetType | "Other",
    local_asset_id: "",
    tags: "",
    archetypes: "",
    notes: ""
  });
  const [editingMappingNotes, setEditingMappingNotes] = useState<{ id: string; notes: string } | null>(null);
  const [mappingNotesSaving, setMappingNotesSaving] = useState(false);
  const [mappingNotesError, setMappingNotesError] = useState<string | null>(null);

  async function importPublicUrl(event: FormEvent) {
    event.preventDefault();
    await publicImportMutation.mutateAsync({
      platform_name: publicForm.platform_name,
      profile_url: publicForm.profile_url
    });
    setPublicForm({ platform_name: "Casting Networks", profile_url: "" });
  }

  async function importProfileDraft(event: FormEvent) {
    event.preventDefault();
    setDraftImportMessage(null);
    setDraftImportError(null);
    if ((!persistentStorageAvailable || !draftFile) && !draftForm.raw_import_text.trim()) {
      setDraftImportError(
        persistentStorageAvailable
          ? "Upload a file, paste profile text, or provide both before creating a draft."
          : "Paste profile text before creating a draft in the hosted demo."
      );
      return;
    }
    const data = new FormData();
    if (actor) data.set("actor_profile_id", actor.id);
    data.set("platform_name", draftForm.platform_name);
    data.set("profile_url", draftForm.profile_url);
    data.set("import_method", draftForm.import_method);
    data.set("raw_import_text", draftForm.raw_import_text);
    if (persistentStorageAvailable && draftFile) data.set("file", draftFile);
    setDraftImportSaving(true);
    try {
      const saved = await uploadMutation.mutateAsync(data);
      setDraftFile(null);
      setDraftFileInputKey((key) => key + 1);
      setDraftForm({ platform_name: "Actors Access", profile_url: "", import_method: "Manual Copy/Paste", raw_import_text: "" });
      setDraftImportMessage(`Created a ${saved.import_status.toLowerCase()} ${saved.platform_name} import. Review it below before approving it into your portfolio.`);
    } catch (error) {
      setDraftImportError(error instanceof Error ? error.message : "Could not create the draft import.");
    } finally {
      setDraftImportSaving(false);
    }
  }

  async function createMapping(event: FormEvent) {
    event.preventDefault();
    await createMappingMutation.mutateAsync({
      platform_name: mappingForm.platform_name,
      platform_asset_name: mappingForm.platform_asset_name,
      asset_type: mappingForm.asset_type,
      local_asset_id: mappingForm.local_asset_id || null,
      tags: splitList(mappingForm.tags),
      archetypes: splitList(mappingForm.archetypes),
      notes: mappingForm.notes || null
    });
    setMappingForm({
      platform_name: "Actors Access",
      platform_asset_name: "",
      asset_type: "Headshot",
      local_asset_id: "",
      tags: "",
      archetypes: "",
      notes: ""
    });
  }

  async function saveMappingNotes(event: FormEvent) {
    event.preventDefault();
    if (!editingMappingNotes) return;
    setMappingNotesSaving(true);
    setMappingNotesError(null);
    try {
      await updateMappingMutation.mutateAsync({ id: editingMappingNotes.id, patch: { notes: editingMappingNotes.notes } });
      setEditingMappingNotes(null);
    } catch (error) {
      setMappingNotesError(error instanceof Error ? error.message : "Could not update mapping notes.");
    } finally {
      setMappingNotesSaving(false);
    }
  }

  return (
    <Section title="Platform Profile Import Assistant" actions={<Clapperboard className="h-5 w-5 text-slate-500" />}>
      <div className="grid gap-4">
        <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          <p className="font-semibold">Compliance boundary</p>
          <p>This assistant only parses information you provide or data visibly returned by a public/shareable profile URL. It does not log in, bypass authentication, scrape hidden account data, download protected media, crawl in the background, or import multiple profiles automatically.</p>
        </div>

        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={importPublicUrl}>
          <div>
            <h3 className="font-semibold">Public / Shareable Profile URL</h3>
            <p className="mt-1 text-sm text-slate-600">One user-triggered fetch of visible page text only.</p>
          </div>
          <Field label="Platform">
            <select className={inputClass} value={publicForm.platform_name} onChange={(e) => setPublicForm({ ...publicForm, platform_name: e.target.value as PlatformName })}>
              {platformNames.map((name) => <option key={name}>{name}</option>)}
            </select>
          </Field>
          <Field label="Public Profile URL">
            <input className={inputClass} type="url" value={publicForm.profile_url} onChange={(e) => setPublicForm({ ...publicForm, profile_url: e.target.value })} placeholder="https://..." required />
          </Field>
          <div className="flex items-end"><Button type="submit">Import Visible Public Data</Button></div>
        </form>

        <div className="grid gap-3 lg:grid-cols-3">
          {publicImports.length === 0 ? null : publicImports.map((item) => (
            <article key={item.id} className="rounded-md border border-slate-200 p-3 text-sm">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold">{String(item.parsed_data_json.profile_name ?? item.platform_name)}</h3>
                  <a className="text-accent hover:underline" href={item.profile_url} target="_blank" rel="noreferrer">{item.platform_name} public link</a>
                </div>
                <Badge>{item.import_status}</Badge>
              </div>
              {item.error_message && (
                <div className="mt-3 rounded bg-amber-50 p-2 text-amber-800">
                  <p className="font-semibold">Import blocked or unavailable</p>
                  <p>{item.error_message}</p>
                  <p className="mt-1">Use copy/paste, PDF upload, screenshot upload, CSV, or guided manual import instead.</p>
                </div>
              )}
              {!item.error_message && (
                <div className="mt-3 rounded bg-slate-50 p-2">
                  <p><strong>Union:</strong> {String(item.parsed_data_json.union_status ?? "Unknown")}</p>
                  <p><strong>Skills:</strong> {Array.isArray(item.parsed_data_json.skills) ? item.parsed_data_json.skills.join(", ") : "None parsed"}</p>
                  <p><strong>Draft assets:</strong> {Array.isArray(item.parsed_data_json.platform_assets) ? item.parsed_data_json.platform_assets.length : 0}</p>
                </div>
              )}
              <details className="mt-3">
                <summary className="cursor-pointer font-semibold text-accent">Review visible parsed draft</summary>
                <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{JSON.stringify(item.parsed_data_json, null, 2)}</pre>
              </details>
              <div className="mt-3 flex flex-wrap gap-2">
                {!item.user_approved && !["Rejected", "Blocked"].includes(item.import_status) && <Button onClick={() => void publicActionMutation.mutateAsync({ id: item.id, action: "approve" })}>Approve Public Import</Button>}
                {item.import_status !== "Rejected" && <Button variant="danger" onClick={() => void publicActionMutation.mutateAsync({ id: item.id, action: "reject" })}>Reject</Button>}
                <Button variant="danger" onClick={() => void publicActionMutation.mutateAsync({ id: item.id, action: "delete" })}>Delete Draft</Button>
              </div>
            </article>
          ))}
        </div>

        <form className="grid gap-3 rounded-md border border-slate-200 p-3" onSubmit={importProfileDraft}>
          <div>
            <h3 className="font-semibold">Create Draft From File, Text, or Both</h3>
            <p className="mt-1 text-sm text-slate-600">
              Upload a profile/resume file, paste profile text or guided form answers, or provide both. The parser combines everything into one reviewable draft.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <Field label="Platform">
              <select name="platform_import_platform" className={inputClass} value={draftForm.platform_name} onChange={(e) => setDraftForm({ ...draftForm, platform_name: e.target.value as PlatformName })}>
                {platformNames.map((name) => <option key={name}>{name}</option>)}
              </select>
            </Field>
            <Field label="Method">
              <select name="platform_import_method" className={inputClass} value={draftForm.import_method} onChange={(e) => setDraftForm({ ...draftForm, import_method: e.target.value as PlatformImportMethod })}>
                {platformImportMethods.map((method) => <option key={method}>{method}</option>)}
              </select>
            </Field>
            <Field label="Profile URL">
              <input name="platform_import_profile_url" className={inputClass} value={draftForm.profile_url} onChange={(e) => setDraftForm({ ...draftForm, profile_url: e.target.value })} placeholder="https://..." />
            </Field>
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            <Field label="Upload File">
              <input
                key={draftFileInputKey}
                name="platform_import_file"
                className={inputClass}
                type="file"
                disabled={!persistentStorageAvailable}
                accept=".pdf,.csv,.txt,.png,.jpg,.jpeg,.webp"
                onChange={(e) => {
                  setDraftFile(e.target.files?.[0] ?? null);
                  setDraftImportMessage(null);
                  setDraftImportError(null);
                }}
              />
            </Field>
            <Field label="Profile Text / Guided Form Answers">
              <textarea
                className={inputClass}
                name="platform_import_text"
                rows={6}
                value={draftForm.raw_import_text}
                onChange={(e) => {
                  setDraftForm({ ...draftForm, raw_import_text: e.target.value });
                  setDraftImportMessage(null);
                  setDraftImportError(null);
                }}
                placeholder="Paste profile, resume, media list, skills, credits, or guided form answers here."
              />
            </Field>
          </div>
          <p className="text-sm text-slate-600">
            {persistentStorageAvailable
              ? "PDF, CSV, and text files are parsed locally. Screenshots are saved as user-provided evidence and may still need pasted text or manual review unless OCR is added later."
              : "File uploads are disabled in the hosted demo because persistent storage is not configured. Paste profile text or guided form answers instead."}
          </p>
          {draftImportMessage && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              {draftImportMessage}
            </div>
          )}
          {draftImportError && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {draftImportError}
            </div>
          )}
          <Button type="submit" disabled={draftImportSaving || ((!persistentStorageAvailable || !draftFile) && !draftForm.raw_import_text.trim())}>
            {draftImportSaving ? "Creating Draft..." : "Create Draft Import"}
          </Button>
        </form>

        <div className="grid gap-3 lg:grid-cols-3">
          {profiles.length === 0 ? <EmptyState>No platform profile imports yet.</EmptyState> : profiles.map((profile) => {
            const structuredCredits = Array.isArray(profile.parsed_profile.structured_credits)
              ? profile.parsed_profile.structured_credits as Record<string, unknown>[]
              : [];
            return (
              <article key={profile.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">{String(profile.parsed_profile.profile_name ?? profile.platform_name)}</h3>
                    <p className="text-slate-600">{profile.platform_name} · {profile.import_method}</p>
                  </div>
                  <Badge>{profile.import_status}</Badge>
                </div>
                {profile.profile_url && <a className="mt-2 inline-block font-semibold text-accent" href={profile.profile_url} target="_blank" rel="noreferrer">Profile URL</a>}
                <div className="mt-3 rounded bg-slate-50 p-2">
                  <p><strong>Union:</strong> {String(profile.parsed_profile.union_status ?? "Unknown")}</p>
                  <p><strong>Playable age:</strong> {profile.parsed_profile.playable_age_range ? JSON.stringify(profile.parsed_profile.playable_age_range) : "Unknown"}</p>
                  <p><strong>Skills:</strong> {Array.isArray(profile.parsed_profile.skills) ? profile.parsed_profile.skills.join(", ") : "None parsed"}</p>
                  <p><strong>Platform media:</strong> {Array.isArray(profile.parsed_profile.platform_assets) ? profile.parsed_profile.platform_assets.length : 0}</p>
                  <p><strong>Resume credits:</strong> {structuredCredits.length}</p>
                </div>
                {structuredCredits.length > 0 && (
                  <div className="mt-3 rounded-md border border-slate-200 p-2">
                    <p className="font-semibold">Parsed Resume Credits</p>
                    <div className="mt-2 grid gap-2">
                      {structuredCredits.slice(0, 6).map((credit, index) => (
                        <div key={`${String(credit.raw_credit ?? credit.project_title ?? "credit")}-${index}`} className="rounded bg-slate-50 p-2">
                          <p className="font-medium">{String(credit.project_title ?? credit.class_or_program ?? credit.raw_credit ?? "Untitled credit")}</p>
                          <p className="text-slate-600">{String(credit.category ?? "Other")} {credit.role_or_character ? `· ${String(credit.role_or_character)}` : ""} {credit.production_company ? `· ${String(credit.production_company)}` : ""}</p>
                        </div>
                      ))}
                    </div>
                    {structuredCredits.length > 6 && <p className="mt-2 text-xs text-slate-500">Showing 6 of {structuredCredits.length}. Approving imports all parsed credits into the Acting Resume Builder for review.</p>}
                  </div>
                )}
                <details className="mt-3">
                  <summary className="cursor-pointer font-semibold text-accent">Review parsed draft</summary>
                  <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">{JSON.stringify(profile.parsed_profile, null, 2)}</pre>
                </details>
                <div className="mt-3 flex flex-wrap gap-2">
                  {!profile.user_approved && profile.import_status !== "Rejected" && <Button onClick={() => void platformActionMutation.mutateAsync({ id: profile.id, action: "approve" })}>Approve & Create Mappings/Credits</Button>}
                  {profile.import_status !== "Rejected" && <Button variant="danger" onClick={() => void platformActionMutation.mutateAsync({ id: profile.id, action: "reject" })}>Reject</Button>}
                  <Button variant="danger" onClick={() => void platformActionMutation.mutateAsync({ id: profile.id, action: "delete" })}>Delete Draft</Button>
                </div>
              </article>
            );
          })}
        </div>

        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-6" onSubmit={createMapping}>
          <div>
            <h3 className="font-semibold">Manual Asset Mapping</h3>
            <p className="mt-1 text-sm text-slate-600">Connect platform-managed names to local assets only when you have provided the file locally.</p>
          </div>
          <Field label="Platform">
            <select className={inputClass} value={mappingForm.platform_name} onChange={(e) => setMappingForm({ ...mappingForm, platform_name: e.target.value as PlatformName })}>
              {platformNames.map((name) => <option key={name}>{name}</option>)}
            </select>
          </Field>
          <Field label="Platform Asset Name">
            <input className={inputClass} value={mappingForm.platform_asset_name} onChange={(e) => setMappingForm({ ...mappingForm, platform_asset_name: e.target.value })} required />
          </Field>
          <Field label="Type">
            <select className={inputClass} value={mappingForm.asset_type} onChange={(e) => setMappingForm({ ...mappingForm, asset_type: e.target.value as AssetType | "Other" })}>
              {[...assetTypes, "Other"].map((type) => <option key={type}>{type}</option>)}
            </select>
          </Field>
          <Field label="Local Asset">
            <select className={inputClass} value={mappingForm.local_asset_id} onChange={(e) => setMappingForm({ ...mappingForm, local_asset_id: e.target.value })}>
              <option value="">Platform-managed only</option>
              {assets.filter((asset) => mappingForm.asset_type === "Other" || asset.asset_type === mappingForm.asset_type).map((asset) => <option key={asset.id} value={asset.id}>{asset.asset_name}</option>)}
            </select>
          </Field>
          <Field label="Tags">
            <input className={inputClass} value={mappingForm.tags} onChange={(e) => setMappingForm({ ...mappingForm, tags: e.target.value })} />
          </Field>
          <Field label="Archetypes">
            <input className={inputClass} value={mappingForm.archetypes} onChange={(e) => setMappingForm({ ...mappingForm, archetypes: e.target.value })} />
          </Field>
          <div className="lg:col-span-5">
            <Field label="Notes">
              <input className={inputClass} value={mappingForm.notes} onChange={(e) => setMappingForm({ ...mappingForm, notes: e.target.value })} />
            </Field>
          </div>
          <div className="flex items-end"><Button type="submit">Create Mapping</Button></div>
        </form>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {mappings.length === 0 ? <EmptyState>No platform asset mappings yet.</EmptyState> : mappings.map((mapping) => {
            const localAsset = assets.find((asset) => asset.id === mapping.local_asset_id);
            return (
              <article key={mapping.id} className="rounded-md border border-slate-200 p-3 text-sm">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">{mapping.platform_asset_name}</h3>
                    <p className="text-slate-600">{mapping.platform_name} · {mapping.asset_type}</p>
                  </div>
                  <Badge>{localAsset ? "Mapped" : "Platform Managed"}</Badge>
                </div>
                <p className="mt-2">Local asset: {localAsset?.asset_name ?? "None"}</p>
                <p>Tags: {mapping.tags.join(", ") || "None"}</p>
                <p>Archetypes: {mapping.archetypes.join(", ") || "None"}</p>
                {mapping.notes && <p className="mt-2 text-slate-600">{mapping.notes}</p>}
                {editingMappingNotes?.id === mapping.id && (
                  <form className="mt-3 grid gap-2 rounded-md border border-slate-200 bg-slate-50 p-2" onSubmit={saveMappingNotes}>
                    <Field label="Mapping Notes">
                      <textarea
                        className={inputClass}
                        rows={3}
                        value={editingMappingNotes.notes}
                        onChange={(event) => setEditingMappingNotes({ ...editingMappingNotes, notes: event.target.value })}
                      />
                    </Field>
                    {mappingNotesError && <p className="text-xs text-red-700">{mappingNotesError}</p>}
                    <div className="flex flex-wrap gap-2">
                      <Button type="submit" disabled={mappingNotesSaving}>{mappingNotesSaving ? "Saving..." : "Save Notes"}</Button>
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setEditingMappingNotes(null);
                          setMappingNotesError(null);
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </form>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setMappingNotesError(null);
                      setEditingMappingNotes({ id: mapping.id, notes: mapping.notes ?? "" });
                    }}
                  >
                    Edit Notes
                  </Button>
                  <Button variant="danger" onClick={() => void deleteMappingMutation.mutateAsync(mapping.id)}>Delete</Button>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </Section>
  );
}
