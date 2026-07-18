import { useEffect, useState, type FormEvent } from "react";
import { Badge, Button, DetailDisclosure, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { joinList, splitList } from "../../../utils/tags";
import type { CareerMemory, ExecutiveBrief } from "../../../types/domain";
import { useExecutiveBriefs, useGenerateWeeklyBrief } from "../hooks/useExecutiveBriefs";

export function ChiefOfStaffPanel({
  memory,
  onSaveMemory
}: {
  memory: CareerMemory | null;
  onSaveMemory: (patch: Partial<CareerMemory>) => Promise<unknown>;
}) {
  const briefs = useExecutiveBriefs();
  return (
    <Section title="Chief of Staff" actions={<GenerateWeeklyBriefButton />}>
      <div className="grid gap-4 xl:grid-cols-2">
        <ChiefOfStaffMemoryPanel memory={memory} onSave={onSaveMemory} />
        <BriefHistoryPanel briefs={briefs.data ?? []} />
      </div>
    </Section>
  );
}

export function ChiefOfStaffMemoryPanel({
  memory,
  onSave
}: {
  memory: CareerMemory | null;
  onSave: (patch: Partial<CareerMemory>) => Promise<unknown>;
}) {
  const [form, setForm] = useState({
    current_career_goals: joinList(memory?.current_career_goals ?? []),
    current_focus: memory?.current_focus ?? "",
    stretch_archetypes: joinList(memory?.stretch_archetypes ?? []),
    preferred_project_types: joinList(memory?.preferred_project_types ?? []),
    preferred_markets: joinList(memory?.preferred_markets ?? []),
    unavailable_dates: joinList(memory?.unavailable_dates ?? []),
    career_notes: memory?.career_notes ?? "",
    executive_notes: memory?.executive_notes ?? ""
  });

  useEffect(() => {
    setForm({
      current_career_goals: joinList(memory?.current_career_goals ?? []),
      current_focus: memory?.current_focus ?? "",
      stretch_archetypes: joinList(memory?.stretch_archetypes ?? []),
      preferred_project_types: joinList(memory?.preferred_project_types ?? []),
      preferred_markets: joinList(memory?.preferred_markets ?? []),
      unavailable_dates: joinList(memory?.unavailable_dates ?? []),
      career_notes: memory?.career_notes ?? "",
      executive_notes: memory?.executive_notes ?? ""
    });
  }, [memory]);

  async function save(event: FormEvent) {
    event.preventDefault();
    await onSave({
      current_career_goals: splitList(form.current_career_goals),
      current_focus: form.current_focus || null,
      stretch_archetypes: splitList(form.stretch_archetypes),
      preferred_project_types: splitList(form.preferred_project_types),
      preferred_markets: splitList(form.preferred_markets),
      unavailable_dates: splitList(form.unavailable_dates),
      career_notes: form.career_notes || null,
      executive_notes: form.executive_notes || null
    });
  }

  return (
    <form className="grid gap-3 rounded-md border border-slate-200 bg-slate-50 p-3" onSubmit={save}>
      <Field label="Current Focus"><input className={inputClass} value={form.current_focus} onChange={(e) => setForm({ ...form, current_focus: e.target.value })} /></Field>
      <Field label="Career Goals"><input className={inputClass} value={form.current_career_goals} onChange={(e) => setForm({ ...form, current_career_goals: e.target.value })} /></Field>
      <Field label="Stretch Archetypes"><input className={inputClass} value={form.stretch_archetypes} onChange={(e) => setForm({ ...form, stretch_archetypes: e.target.value })} /></Field>
      <Field label="Preferred Project Types"><input className={inputClass} value={form.preferred_project_types} onChange={(e) => setForm({ ...form, preferred_project_types: e.target.value })} /></Field>
      <Field label="Preferred Markets"><input className={inputClass} value={form.preferred_markets} onChange={(e) => setForm({ ...form, preferred_markets: e.target.value })} /></Field>
      <Field label="Unavailable Dates"><input className={inputClass} value={form.unavailable_dates} onChange={(e) => setForm({ ...form, unavailable_dates: e.target.value })} /></Field>
      <Field label="Career Notes"><textarea className={inputClass} value={form.career_notes} onChange={(e) => setForm({ ...form, career_notes: e.target.value })} /></Field>
      <Field label="Chief of Staff Notes"><textarea className={inputClass} value={form.executive_notes} onChange={(e) => setForm({ ...form, executive_notes: e.target.value })} /></Field>
      <Button type="submit">Save Career Memory</Button>
    </form>
  );
}

export function BriefHistoryPanel({ briefs }: { briefs: ExecutiveBrief[] }) {
  if (briefs.length === 0) {
    return <EmptyState>Generate a weekly brief to summarize progress and next priorities.</EmptyState>;
  }
  return (
    <div className="grid gap-3">
      {briefs.slice(0, 3).map((brief) => (
        <WeeklyBriefPanel key={brief.id} brief={brief} />
      ))}
    </div>
  );
}

export function WeeklyBriefPanel({ brief }: { brief: ExecutiveBrief }) {
  return (
    <article className="rounded-md border border-slate-200 p-3 text-sm">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold">{brief.brief_type} Brief</h3>
          <p className="text-slate-600">{brief.period_start} to {brief.period_end}</p>
        </div>
        <Badge>{brief.recommended_priorities.length} priorities</Badge>
      </div>
      <p className="mt-2 text-slate-700">{brief.summary}</p>
      <DetailDisclosure label="Weekly Signals" defaultOpen={false}>
        <p>Breakdowns: {brief.new_matching_breakdowns.length}</p>
        <p>Submissions: {brief.submissions_completed.length}</p>
        <p>Callbacks: {brief.callbacks_received.length}</p>
        <p>Bookings: {brief.bookings.length}</p>
      </DetailDisclosure>
    </article>
  );
}

function GenerateWeeklyBriefButton() {
  const generate = useGenerateWeeklyBrief();
  return (
    <Button
      variant="secondary"
      onClick={async () => {
        await generate.mutateAsync();
      }}
    >
      Generate Weekly Brief
    </Button>
  );
}
