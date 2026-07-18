import { useRef, useState } from "react";
import { ActionCard, Badge, Button, ConfirmAction, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { assetFileUrl } from "../api";
import { assetTypes } from "../constants";
import { useMaterialLibrary } from "../hooks/useMaterialLibrary";
import type { ActorProfile, AssetType, SystemCapabilities } from "../types";
import { MaterialEditForm } from "./MaterialEditForm";

export function AssetLibrary({
  actor,
  capabilities
}: {
  actor: ActorProfile | null;
  capabilities?: SystemCapabilities | null;
}) {
  const aiConfigured = capabilities?.flags.ai_configured ?? false;
  const suggestionLabel = aiConfigured ? "AI-assisted tags" : "Suggested Tags";
  const analysisLabel = aiConfigured ? "AI analysis" : "Deterministic Recommendation";
  const library = useMaterialLibrary({ actor });
  const [editingAssetId, setEditingAssetId] = useState<string | null>(null);
  const lastEditButtonRef = useRef<HTMLButtonElement | null>(null);

  function closeEditForm() {
    setEditingAssetId(null);
    window.setTimeout(() => lastEditButtonRef.current?.focus(), 0);
  }

  return (
    <Section title="Materials" actions={<Button onClick={() => library.setFormOpen((current) => !current)}>{library.formOpen ? "Hide Form" : "Upload Material"}</Button>}>
      {library.isLoading && <p role="status" className="mb-3 text-sm text-slate-600">Loading Materials...</p>}
      {library.queryError && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm font-medium text-red-800">{library.queryError}</p>}
      {library.isRefetching && !library.isLoading && <p role="status" className="mb-3 text-xs text-slate-500">Refreshing Materials...</p>}
      {!actor ? <EmptyState>Create an actor profile before uploading assets.</EmptyState> : (
        library.formOpen && (
          <form className="mb-4 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 lg:grid-cols-6" onSubmit={library.submit}>
            <Field label="Name"><input name="material_name" className={inputClass} value={library.form.asset_name} onChange={(e) => library.setForm({ ...library.form, asset_name: e.target.value })} required /></Field>
            <Field label="Type"><select name="material_type" className={inputClass} value={library.form.asset_type} onChange={(e) => library.setForm({ ...library.form, asset_type: e.target.value as AssetType })}>{assetTypes.map((type) => <option key={type}>{type}</option>)}</select></Field>
            <Field label="Tags"><input name="material_tags" className={inputClass} value={library.form.tags} onChange={(e) => library.setForm({ ...library.form, tags: e.target.value })} /></Field>
            <Field label="Archetypes"><input name="material_archetypes" className={inputClass} value={library.form.archetype_names} onChange={(e) => library.setForm({ ...library.form, archetype_names: e.target.value })} /></Field>
            <Field label="File">
              <input
                key={library.fileInputKey}
                name="material_file"
                className={inputClass}
                type="file"
                onChange={(e) => library.selectFile(e.target.files?.[0] ?? null)}
                required
              />
            </Field>
            <div className="flex items-end"><Button type="submit" disabled={library.saving || !library.file}>{library.saving ? "Uploading..." : "Upload"}</Button></div>
            {library.file && <p className="text-xs text-slate-600 lg:col-span-6">Selected file: {library.file.name}</p>}
            {library.message && <p className="rounded bg-emerald-50 p-2 text-sm font-medium text-emerald-800 lg:col-span-6">{library.message}</p>}
          </form>
        )
      )}
      {library.error && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm font-medium text-red-800">{library.error}</p>}
      {library.deletePending && <p role="status" className="mb-3 text-xs text-slate-500">Deleting material...</p>}
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {!library.isLoading && !library.queryError && library.assets.length === 0 ? <EmptyState>Upload your first headshot, reel, slate, or resume.</EmptyState> : library.assets.map((asset) => (
          <ActionCard
            key={asset.id}
            title={asset.asset_name}
            status={<Badge>{asset.freshness_status}</Badge>}
            meta={`${asset.asset_type} · ${analysisLabel}`}
            primaryAction={<a className="inline-flex items-center justify-center rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50" href={assetFileUrl(asset.id)} target="_blank" rel="noreferrer">View</a>}
            secondaryAction={(
              <>
                <Button variant="secondary" disabled={library.analyzePending} onClick={() => void library.analyze(asset.id)}>{library.analyzePending ? "Analyzing..." : "Analyze"}</Button>
                <button
                  type="button"
                  className="inline-flex min-w-0 max-w-full items-center justify-center whitespace-normal break-words rounded-md border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-ink transition hover:bg-slate-50"
                  ref={(element) => {
                    if (editingAssetId === asset.id && element) lastEditButtonRef.current = element;
                  }}
                  onClick={(event) => {
                    lastEditButtonRef.current = event.currentTarget;
                    setEditingAssetId((current) => current === asset.id ? null : asset.id);
                  }}
                >
                  Edit
                </button>
                <ConfirmAction
                  label="Delete"
                  confirmLabel="Delete"
                  message={`Delete ${asset.asset_name}?`}
                  onConfirm={() => library.remove(asset.id)}
                />
              </>
            )}
            details={(
              <div className="grid gap-2">
                {editingAssetId === asset.id && (
                  <MaterialEditForm
                    asset={asset}
                    onSave={library.saveEdit}
                    onCancel={closeEditForm}
                  />
                )}
                <DetailDisclosure label="Tags and Archetypes">
                  <div className="flex flex-wrap gap-1">
                    {[...asset.tags, ...asset.archetype_names].length === 0 ? "No tags yet." : [...asset.tags, ...asset.archetype_names].map((tag) => <Badge key={tag}>{tag}</Badge>)}
                  </div>
                </DetailDisclosure>
                <DetailDisclosure label="Freshness">
                  <p>Updated: {asset.last_updated_date ?? "Unknown"}</p>
                  <p>Last used: {asset.last_used_date ?? "Never"}</p>
                  <p>Warning date: {asset.expiration_warning_date ?? "Not set"}</p>
                </DetailDisclosure>
                {(asset.ai_suggested_tags.length > 0 || asset.ai_suggested_archetypes.length > 0) && (
                  <DetailDisclosure label={suggestionLabel}>
                    <p>Tags: {asset.ai_suggested_tags.join(", ") || "None"}</p>
                    <p>Archetypes: {asset.ai_suggested_archetypes.join(", ") || "None"}</p>
                    {!aiConfigured && <p className="mt-2 text-slate-500">These are rule-based suggestions. Connect an AI provider to enable AI-assisted tagging.</p>}
                  </DetailDisclosure>
                )}
              </div>
            )}
          />
        ))}
      </div>
    </Section>
  );
}
