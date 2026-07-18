import { useEffect, useRef, useState, type FormEvent } from "react";
import { AsyncButton, Button, Field, inputClass } from "../../../components/ui";
import { joinList, splitList } from "../../../utils/tags";
import { assetTypes } from "../constants";
import type { Asset, AssetType } from "../types";

const freshnessStatuses: Asset["freshness_status"][] = ["Current", "Aging", "Needs Review", "Outdated"];

export function MaterialEditForm({
  asset,
  onSave,
  onCancel
}: {
  asset: Asset;
  onSave: (assetId: string, payload: {
    asset_name: string;
    asset_type: AssetType;
    description: string | null;
    tags: string[];
    archetype_names: string[];
    freshness_status: Asset["freshness_status"];
  }) => Promise<void>;
  onCancel: () => void;
}) {
  const firstFieldRef = useRef<HTMLInputElement>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    asset_name: asset.asset_name,
    asset_type: asset.asset_type,
    description: asset.description ?? "",
    tags: joinList(asset.tags),
    archetype_names: joinList(asset.archetype_names),
    freshness_status: asset.freshness_status
  });

  useEffect(() => {
    firstFieldRef.current?.focus();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(asset.id, {
        asset_name: form.asset_name,
        asset_type: form.asset_type,
        description: form.description || null,
        tags: splitList(form.tags),
        archetype_names: splitList(form.archetype_names),
        freshness_status: form.freshness_status
      });
      onCancel();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save this material.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="mt-3 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={(event) => void submit(event)}>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Material Name">
          <input ref={firstFieldRef} name="edit_material_name" className={inputClass} value={form.asset_name} onChange={(event) => setForm({ ...form, asset_name: event.target.value })} required />
        </Field>
        <Field label="Material Type">
          <select name="edit_material_type" className={inputClass} value={form.asset_type} onChange={(event) => setForm({ ...form, asset_type: event.target.value as AssetType })}>
            {assetTypes.map((type) => <option key={type}>{type}</option>)}
          </select>
        </Field>
        <Field label="Tags">
          <input name="edit_material_tags" className={inputClass} value={form.tags} onChange={(event) => setForm({ ...form, tags: event.target.value })} />
        </Field>
        <Field label="Archetypes">
          <input name="edit_material_archetypes" className={inputClass} value={form.archetype_names} onChange={(event) => setForm({ ...form, archetype_names: event.target.value })} />
        </Field>
        <Field label="Freshness Status">
          <select name="edit_material_freshness" className={inputClass} value={form.freshness_status} onChange={(event) => setForm({ ...form, freshness_status: event.target.value as Asset["freshness_status"] })}>
            {freshnessStatuses.map((status) => <option key={status}>{status}</option>)}
          </select>
        </Field>
        <div className="md:col-span-2">
          <Field label="Notes">
            <textarea name="edit_material_description" className={inputClass} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          </Field>
        </div>
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-sm font-medium text-red-800">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <AsyncButton type="submit" loading={saving}>Save Material</AsyncButton>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}
