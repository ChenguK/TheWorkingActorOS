import type { ActorJournalEntry, CareerDevelopmentTask } from "../../../types/domain";
import type { OpportunityOption } from "../../breakdowns";
import type { MaterialOption } from "../../materials";
import type { JournalDateGroup, JournalFormState, JournalLinkedEntity } from "../types";

export function createBlankJournalForm(): JournalFormState {
  return {
    date: new Date().toISOString().slice(0, 10),
    event_type: "Manual",
    title: "",
    description: "",
    linked_breakdown_id: "",
    linked_audition_id: "",
    linked_material_id: "",
    linked_career_task_id: "",
    notes: ""
  };
}

export function groupJournalEntriesByDate(entries: ActorJournalEntry[]): JournalDateGroup[] {
  const groups = new Map<string, ActorJournalEntry[]>();
  entries.forEach((entry) => {
    const rows = groups.get(entry.date) ?? [];
    rows.push(entry);
    groups.set(entry.date, rows);
  });
  return Array.from(groups.entries()).sort(([a], [b]) => b.localeCompare(a));
}

export function formatJournalDate(value: string): string {
  const parsed = new Date(`${value}T12:00:00`);
  return parsed.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

export function journalEntryLinks({
  entry,
  opportunities,
  assets,
  careerTasks
}: {
  entry: ActorJournalEntry;
  opportunities: OpportunityOption[];
  assets: MaterialOption[];
  careerTasks: CareerDevelopmentTask[];
}): JournalLinkedEntity[] {
  const breakdown = entry.linked_breakdown_id ? opportunities.find((item) => item.id === entry.linked_breakdown_id) : null;
  const material = entry.linked_material_id ? assets.find((item) => item.id === entry.linked_material_id) : null;
  const task = entry.linked_career_task_id ? careerTasks.find((item) => item.id === entry.linked_career_task_id) : null;
  return [
    breakdown ? { key: "breakdown", href: `/auditions?breakdownId=${breakdown.id}`, label: `${breakdown.role} breakdown` } : null,
    entry.linked_audition_id ? { key: "audition", href: "/auditions", label: "Audition" } : null,
    material ? { key: "material", href: "/materials", label: material.asset_name } : null,
    task ? { key: "task", href: "/career", label: task.title } : null
  ].filter(Boolean) as JournalLinkedEntity[];
}
