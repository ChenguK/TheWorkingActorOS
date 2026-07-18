import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Briefcase, Clapperboard, Download, Edit3, Eye, EyeOff, MapPin, Save, Star, Trash2, UserRound, X } from "lucide-react";
import { Badge, Button, CapabilityNotice, EmptyState, Field, Section, StatusBadge, inputClass } from "../../../components/ui";
import { formatDateTime } from "../../../utils/dateTime";
import { joinList, splitList } from "../../../utils/tags";
import type {
  ActingCredit,
  ActingCreditCategory,
  ActorProfile,
  Asset,
  AssetType,
  CastingPlatformSubscription,
  PlatformAssetMapping,
  PlatformImportMethod,
  PlatformName,
  PlatformProfile,
  ProfessionalEquipmentProfile,
  PublicProfileImport,
  Representation,
  TravelPreference
} from "../../../types/domain";
import { generatedResumeDocxUrl, generatedResumePdfUrl } from "../api";
import { useCreateActingCredit, useDeleteActingCredit, useUpdateActingCredit } from "../hooks/useProfileQueries";
import { actingCreditCategories } from "./ProfileFormShared";

export function ActingResumeBuilder({ actor, credits }: { actor: ActorProfile | null; credits: ActingCredit[] }) {
  const createMutation = useCreateActingCredit();
  const updateMutation = useUpdateActingCredit();
  const deleteMutation = useDeleteActingCredit();
  const blankCreditForm = {
    category: "Television" as ActingCreditCategory,
    project_title: "",
    role_or_character: "",
    role_type: "",
    production_company: "",
    network_or_distributor: "",
    director: "",
    episode_title: "",
    season_episode: "",
    year: "",
    union_status: "",
    class_or_program: "",
    instructor: "",
    institution: "",
    skill_name: "",
    skill_category: "",
    proficiency: "",
    notes: "",
    display_order: "",
    section_order: "",
    highlighted: false
  };
  const [form, setForm] = useState(blankCreditForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(blankCreditForm);

  const grouped = useMemo(() => {
    const entries = [...credits].sort((a, b) => a.section_order - b.section_order || a.display_order - b.display_order);
    return actingCreditCategories.map((category) => ({
      category,
      enabled: entries.find((credit) => credit.category === category)?.section_enabled ?? true,
      sectionOrder: entries.find((credit) => credit.category === category)?.section_order ?? actingCreditCategories.indexOf(category),
      items: entries.filter((credit) => credit.category === category)
    })).filter((section) => section.items.length > 0 || section.enabled)
      .sort((a, b) => a.sectionOrder - b.sectionOrder || actingCreditCategories.indexOf(a.category) - actingCreditCategories.indexOf(b.category));
  }, [credits]);

  function creditToForm(credit: ActingCredit) {
    return {
      category: credit.category,
      project_title: credit.project_title ?? "",
      role_or_character: credit.role_or_character ?? "",
      role_type: credit.role_type ?? "",
      production_company: credit.production_company ?? "",
      network_or_distributor: credit.network_or_distributor ?? "",
      director: credit.director ?? "",
      episode_title: credit.episode_title ?? "",
      season_episode: credit.season_episode ?? "",
      year: credit.year ?? "",
      union_status: credit.union_status ?? "",
      class_or_program: credit.class_or_program ?? "",
      instructor: credit.instructor ?? "",
      institution: credit.institution ?? "",
      skill_name: credit.skill_name ?? "",
      skill_category: credit.skill_category ?? "",
      proficiency: credit.proficiency ?? "",
      notes: credit.notes ?? "",
      display_order: String(credit.display_order),
      section_order: String(credit.section_order),
      highlighted: credit.highlighted
    };
  }

  function creditPayload(source: typeof blankCreditForm) {
    return {
      category: source.category,
      section_order: Number(source.section_order || actingCreditCategories.indexOf(source.category)),
      display_order: Number(source.display_order || 0),
      highlighted: source.highlighted,
      project_title: source.project_title || null,
      role_or_character: source.role_or_character || null,
      role_type: source.role_type || null,
      production_company: source.production_company || null,
      network_or_distributor: source.network_or_distributor || null,
      director: source.director || null,
      episode_title: source.episode_title || null,
      season_episode: source.season_episode || null,
      year: source.year || null,
      union_status: source.union_status || null,
      class_or_program: source.class_or_program || null,
      instructor: source.instructor || null,
      institution: source.institution || null,
      skill_name: source.skill_name || null,
      skill_category: source.skill_category || null,
      proficiency: source.proficiency || null,
      notes: source.notes || null
    };
  }

  async function createCredit(event: FormEvent) {
    event.preventDefault();
    if (!actor) return;
    await createMutation.mutateAsync({
      actor_profile_id: actor.id,
      section_enabled: true,
      ...creditPayload({
        ...form,
        display_order: form.display_order || String(credits.filter((credit) => credit.category === form.category).length)
      })
    });
    setForm(blankCreditForm);
  }

  async function saveEdit(credit: ActingCredit) {
    await updateMutation.mutateAsync({ id: credit.id, patch: creditPayload(editForm) });
    setEditingId(null);
  }

  async function moveCredit(credit: ActingCredit, direction: -1 | 1) {
    await updateMutation.mutateAsync({ id: credit.id, patch: { display_order: credit.display_order + direction } });
  }

  async function toggleSection(category: ActingCreditCategory, enabled: boolean) {
    await Promise.all(credits.filter((credit) => credit.category === category).map((credit) => updateMutation.mutateAsync({ id: credit.id, patch: { section_enabled: enabled } })));
  }

  async function moveSection(index: number, direction: -1 | 1) {
    const targetIndex = index + direction;
    const current = grouped[index];
    const target = grouped[targetIndex];
    if (!current || !target) return;
    await Promise.all([
      ...credits
        .filter((credit) => credit.category === current.category)
        .map((credit) => updateMutation.mutateAsync({ id: credit.id, patch: { section_order: target.sectionOrder } })),
      ...credits
        .filter((credit) => credit.category === target.category)
        .map((credit) => updateMutation.mutateAsync({ id: credit.id, patch: { section_order: current.sectionOrder } }))
    ]);
  }

  function IconButton({ title, children, variant = "secondary", onClick }: { title: string; children: ReactNode; variant?: "secondary" | "danger"; onClick: () => void }) {
    const classes = variant === "danger"
      ? "bg-red-600 text-white hover:bg-red-700"
      : "border border-slate-300 bg-white text-ink hover:bg-slate-50";
    return (
      <button type="button" title={title} aria-label={title} onClick={onClick} className={`inline-flex h-8 w-8 items-center justify-center rounded-md transition ${classes}`}>
        {children}
      </button>
    );
  }

  function HeaderRow({ category }: { category: ActingCreditCategory }) {
    const labels = category === "Training"
      ? ["Class / Program", "Teacher", "Institution", "Year"]
      : category === "Special Skills"
        ? ["Skill", "Category", "Proficiency", "Notes"]
        : category === "Theater"
          ? ["Project Name", "Role", "Theater", "Director"]
        : ["Project Name", "Role", "Producer / Channel", "Director"];
    return (
      <div className="hidden rounded bg-slate-100 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600 md:grid md:grid-cols-4">
        {labels.map((label) => <span key={label}>{label}</span>)}
      </div>
    );
  }

  function creditPreviewValues(category: ActingCreditCategory, credit: ActingCredit): string[] {
    if (category === "Training") {
      return [
        credit.class_or_program || "",
        credit.instructor || "",
        credit.institution || "",
        credit.year || ""
      ];
    }
    if (category === "Special Skills") {
      return [
        credit.skill_name || "",
        credit.skill_category || "",
        credit.proficiency || "",
        credit.notes || ""
      ];
    }
    if (category === "Theater") {
      return [
        credit.project_title || "",
        credit.role_or_character || credit.role_type || "",
        credit.production_company || "",
        credit.director || ""
      ];
    }
    return [
      credit.project_title || "",
      credit.role_or_character || credit.role_type || "",
      credit.network_or_distributor || credit.production_company || "",
      credit.director || ""
    ];
  }

  function CreditFields({ value, onChange }: { value: typeof blankCreditForm; onChange: (next: typeof blankCreditForm) => void }) {
    return (
      <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 lg:grid-cols-4">
        <Field label="Section">
          <select name="resume_credit_category" className={inputClass} value={value.category} onChange={(e) => onChange({ ...value, category: e.target.value as ActingCreditCategory })}>
            {actingCreditCategories.map((category) => <option key={category}>{category}</option>)}
          </select>
        </Field>
        {value.category === "Training" ? (
          <>
            <Field label="Class / Program"><input name="resume_credit_class_or_program" className={inputClass} value={value.class_or_program} onChange={(e) => onChange({ ...value, class_or_program: e.target.value })} /></Field>
            <Field label="Teacher"><input name="resume_credit_teacher" className={inputClass} value={value.instructor} onChange={(e) => onChange({ ...value, instructor: e.target.value })} /></Field>
            <Field label="Institution"><input name="resume_credit_institution" className={inputClass} value={value.institution} onChange={(e) => onChange({ ...value, institution: e.target.value })} /></Field>
          </>
        ) : value.category === "Special Skills" ? (
          <>
            <Field label="Skill"><input name="resume_credit_skill" className={inputClass} value={value.skill_name} onChange={(e) => onChange({ ...value, skill_name: e.target.value })} /></Field>
            <Field label="Skill Category"><input name="resume_credit_skill_category" className={inputClass} value={value.skill_category} onChange={(e) => onChange({ ...value, skill_category: e.target.value })} /></Field>
            <Field label="Proficiency"><input name="resume_credit_proficiency" className={inputClass} value={value.proficiency} onChange={(e) => onChange({ ...value, proficiency: e.target.value })} /></Field>
          </>
        ) : (
          <>
            <Field label="Project Name"><input name="resume_credit_project_name" className={inputClass} value={value.project_title} onChange={(e) => onChange({ ...value, project_title: e.target.value })} /></Field>
            <Field label="Role"><input name="resume_credit_role" className={inputClass} value={value.role_or_character} onChange={(e) => onChange({ ...value, role_or_character: e.target.value })} /></Field>
            <Field label="Role Type"><input name="resume_credit_role_type" className={inputClass} value={value.role_type} onChange={(e) => onChange({ ...value, role_type: e.target.value })} /></Field>
            <Field label="Production Company"><input name="resume_credit_production_company" className={inputClass} value={value.production_company} onChange={(e) => onChange({ ...value, production_company: e.target.value })} /></Field>
            <Field label="Producer / Channel"><input name="resume_credit_producer_channel" className={inputClass} value={value.network_or_distributor} onChange={(e) => onChange({ ...value, network_or_distributor: e.target.value })} /></Field>
            <Field label="Director"><input name="resume_credit_director" className={inputClass} value={value.director} onChange={(e) => onChange({ ...value, director: e.target.value })} /></Field>
            <Field label="Episode"><input name="resume_credit_episode" className={inputClass} value={value.episode_title} onChange={(e) => onChange({ ...value, episode_title: e.target.value })} /></Field>
            <Field label="Season / Episode"><input name="resume_credit_season_episode" className={inputClass} value={value.season_episode} onChange={(e) => onChange({ ...value, season_episode: e.target.value })} /></Field>
          </>
        )}
        <Field label="Year"><input name="resume_credit_year" className={inputClass} value={value.year} onChange={(e) => onChange({ ...value, year: e.target.value })} /></Field>
        <Field label="Union"><input name="resume_credit_union" className={inputClass} value={value.union_status} onChange={(e) => onChange({ ...value, union_status: e.target.value })} /></Field>
        <Field label="Display Order"><input name="resume_credit_display_order" className={inputClass} type="number" value={value.display_order} onChange={(e) => onChange({ ...value, display_order: e.target.value })} /></Field>
        <label className="flex items-center gap-2 text-sm text-slate-700"><input name="resume_credit_highlighted" type="checkbox" checked={value.highlighted} onChange={(e) => onChange({ ...value, highlighted: e.target.checked })} /> Highlight</label>
        <div className="lg:col-span-4"><Field label="Notes"><input name="resume_credit_notes" className={inputClass} value={value.notes} onChange={(e) => onChange({ ...value, notes: e.target.value })} /></Field></div>
      </div>
    );
  }

  return (
    <Section
      title="Acting Resume Builder"
      actions={
        <>
          {actor && (
            <>
              <a className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50" href={generatedResumePdfUrl(actor.id)} target="_blank" rel="noreferrer">
                <Download className="h-4 w-4" /> PDF
              </a>
              <a className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-ink transition hover:bg-slate-50" href={generatedResumeDocxUrl(actor.id)} target="_blank" rel="noreferrer">
                <Download className="h-4 w-4" /> DOCX
              </a>
            </>
          )}
          <Briefcase className="h-5 w-5 text-slate-500" />
        </>
      }
    >
      <div className="grid gap-4">
        <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          <p>Every saved resume edit regenerates one current PDF for submissions and removes the previous generated resume file to save space.</p>
        </div>
        <form className="grid gap-3 rounded-md border border-slate-200 p-3 lg:grid-cols-4" onSubmit={createCredit}>
          {!actor && <p className="text-sm text-red-700 lg:col-span-4">Create an actor profile before adding credits.</p>}
          <div className="lg:col-span-4"><CreditFields value={form} onChange={setForm} /></div>
          <div className="flex items-end"><Button type="submit" disabled={!actor}>Add Credit</Button></div>
        </form>

        <div className="rounded-md border border-slate-200 p-4">
          <h3 className="font-semibold">Casting-Profile Preview</h3>
          <div className="mt-4 grid gap-4">
            {grouped.map((section, sectionIndex) => (
              <div key={section.category} className={section.enabled ? "" : "opacity-50"}>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <h4 className="font-semibold uppercase tracking-wide">{section.category}</h4>
                  <div className="flex items-center gap-2">
                    <IconButton title="Move section up" onClick={() => moveSection(sectionIndex, -1)}><ArrowUp className="h-4 w-4" /></IconButton>
                    <IconButton title="Move section down" onClick={() => moveSection(sectionIndex, 1)}><ArrowDown className="h-4 w-4" /></IconButton>
                    <IconButton title={section.enabled ? "Hide section" : "Show section"} onClick={() => toggleSection(section.category, !section.enabled)}>
                      {section.enabled ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </IconButton>
                  </div>
                </div>
                <div className="grid gap-2">
                  <HeaderRow category={section.category} />
                  {section.items.length === 0 ? <p className="text-sm text-slate-500">No credits yet.</p> : section.items.map((credit) => (
                    <article key={credit.id} className={`rounded border p-2 text-sm ${credit.highlighted ? "border-blue-300 bg-blue-50" : "border-slate-200"}`}>
                      {editingId === credit.id ? (
                        <div className="grid gap-3">
                          <CreditFields value={editForm} onChange={setEditForm} />
                          <div className="flex flex-wrap gap-2">
                            <IconButton title="Save credit" onClick={() => saveEdit(credit)}><Save className="h-4 w-4" /></IconButton>
                            <IconButton title="Cancel edit" onClick={() => setEditingId(null)}><X className="h-4 w-4" /></IconButton>
                          </div>
                        </div>
                      ) : (
                        <>
                          {(() => {
                            const values = creditPreviewValues(section.category, credit);
                            return (
                          <div className="grid gap-1 md:grid-cols-4">
                            <p className="font-semibold">{values[0] || "Untitled"}</p>
                            <p>{values[1]}</p>
                            <p>{values[2]}</p>
                            <p>{values[3]}</p>
                          </div>
                            );
                          })()}
                          <div className="mt-2 flex flex-wrap gap-2">
                            <IconButton title="Move up" onClick={() => moveCredit(credit, -1)}><ArrowUp className="h-4 w-4" /></IconButton>
                            <IconButton title="Move down" onClick={() => moveCredit(credit, 1)}><ArrowDown className="h-4 w-4" /></IconButton>
                            <IconButton title="Edit credit" onClick={() => { setEditingId(credit.id); setEditForm(creditToForm(credit)); }}><Edit3 className="h-4 w-4" /></IconButton>
                            <IconButton title={credit.highlighted ? "Remove highlight" : "Highlight credit"} onClick={() => void updateMutation.mutateAsync({ id: credit.id, patch: { highlighted: !credit.highlighted } })}><Star className={`h-4 w-4 ${credit.highlighted ? "fill-current" : ""}`} /></IconButton>
                            <IconButton title="Delete credit" variant="danger" onClick={() => void deleteMutation.mutateAsync(credit.id)}><Trash2 className="h-4 w-4" /></IconButton>
                          </div>
                        </>
                      )}
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Section>
  );
}
