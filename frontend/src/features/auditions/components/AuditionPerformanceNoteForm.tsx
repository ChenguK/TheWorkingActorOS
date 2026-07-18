import { useEffect, useRef, useState, type FormEvent } from "react";
import { AsyncButton, Button, Field, inputClass } from "../../../components/ui";
import type { AuditionJournalEntry, AuditionNoteFormState } from "../types";

export function AuditionPerformanceNoteForm({
  entry,
  onSave,
  onCancel
}: {
  entry: AuditionJournalEntry;
  onSave: (entryId: string, patch: Partial<AuditionNoteFormState>) => Promise<void>;
  onCancel: () => void;
}) {
  const firstFieldRef = useRef<HTMLTextAreaElement>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    preparation_notes: entry.preparation_notes ?? "",
    performance_notes: entry.performance_notes ?? "",
    casting_notes: entry.casting_notes ?? "",
    wardrobe_notes: entry.wardrobe_notes ?? "",
    emotional_notes: entry.emotional_notes ?? "",
    follow_up_notes: entry.follow_up_notes ?? ""
  });

  useEffect(() => {
    firstFieldRef.current?.focus();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await onSave(entry.id, form);
      onCancel();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Could not save these private audition notes.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="mt-3 grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={(event) => void submit(event)}>
      <div className="grid gap-3 md:grid-cols-2">
        <Field label="Preparation">
          <textarea
            ref={firstFieldRef}
            name="edit_audition_preparation_notes"
            className={inputClass}
            value={form.preparation_notes}
            onChange={(event) => setForm({ ...form, preparation_notes: event.target.value })}
          />
        </Field>
        <Field label="Performance">
          <textarea
            name="edit_audition_performance_notes"
            className={inputClass}
            value={form.performance_notes}
            onChange={(event) => setForm({ ...form, performance_notes: event.target.value })}
          />
        </Field>
        <Field label="Casting Notes">
          <textarea
            name="edit_audition_casting_notes"
            className={inputClass}
            value={form.casting_notes}
            onChange={(event) => setForm({ ...form, casting_notes: event.target.value })}
          />
        </Field>
        <Field label="Wardrobe">
          <textarea
            name="edit_audition_wardrobe_notes"
            className={inputClass}
            value={form.wardrobe_notes}
            onChange={(event) => setForm({ ...form, wardrobe_notes: event.target.value })}
          />
        </Field>
        <Field label="Emotional Notes">
          <textarea
            name="edit_audition_emotional_notes"
            className={inputClass}
            value={form.emotional_notes}
            onChange={(event) => setForm({ ...form, emotional_notes: event.target.value })}
          />
        </Field>
        <Field label="Follow-Up Notes">
          <textarea
            name="edit_audition_follow_up_notes"
            className={inputClass}
            value={form.follow_up_notes}
            onChange={(event) => setForm({ ...form, follow_up_notes: event.target.value })}
          />
        </Field>
      </div>
      {error && <p className="rounded bg-red-50 p-2 text-sm font-medium text-red-800">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <AsyncButton type="submit" loading={saving}>Save Private Notes</AsyncButton>
        <Button type="button" variant="secondary" onClick={onCancel}>Cancel</Button>
      </div>
    </form>
  );
}
