import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { ArrowDown, ArrowUp, Briefcase, Clapperboard, Download, Edit3, Eye, EyeOff, MapPin, Save, Star, Trash2, UserRound, X } from "lucide-react";
import { Badge, Button, CapabilityNotice, EmptyState, Field, Section, StatusBadge, inputClass } from "../../../components/ui";
import {
  accentOptions,
  disabilityIdentityOptions,
  ethnicityOptions,
  genderExpressionOptions,
  genderIdentityOptions,
  languageOptions,
  nationalityOptions,
  pronounOptions,
  raceIdentityOptions
} from "../../../constants/demographicOptions";
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
import { defaultExcludedRoleTypes, defaultIncludedRoleTypes } from "../../../constants/workflowOptions";
import { useCreateRepresentation, useDeleteRepresentation, useUpdateActorProfile, useUpdateRepresentation } from "../hooks/useProfileQueries";
import {
  blankProfile,
  DemographicOptionPicker,
  representationTypes,
  roleTypePreferenceOptions,
  SavedField,
  type ActorProfileForm
} from "./ProfileFormShared";

export function ActorProfilePanel({
  actor,
  representations
}: {
  actor: ActorProfile | null;
  representations: Representation[];
}) {
  const actorMutation = useUpdateActorProfile();
  const createRepresentationMutation = useCreateRepresentation();
  const updateRepresentationMutation = useUpdateRepresentation();
  const deleteRepresentationMutation = useDeleteRepresentation();
  const [form, setForm] = useState<ActorProfileForm>(blankProfile);
  const [representationForm, setRepresentationForm] = useState({
    agency_name: "",
    agent_name: "",
    agent_email: "",
    agent_phone: "",
    agency_website: "",
    representation_type: "Theatrical" as Representation["representation_type"],
    market: "",
    notes: "",
    active: true,
    start_date: "",
    end_date: ""
  });
  const [saving, setSaving] = useState(false);
  const [profileMessage, setProfileMessage] = useState<string | null>(null);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [representationSaving, setRepresentationSaving] = useState(false);
  const [representationMessage, setRepresentationMessage] = useState<string | null>(null);
  const [representationError, setRepresentationError] = useState<string | null>(null);
  const [profileFormOpen, setProfileFormOpen] = useState(false);
  const [representationFormOpen, setRepresentationFormOpen] = useState(false);
  const [editingRepresentationId, setEditingRepresentationId] = useState<string | null>(null);

  useEffect(() => {
    if (actor) {
      setForm({
        name: actor.name,
        sag_status: actor.sag_status,
        union_status: actor.union_status,
        current_location: actor.current_location,
        playable_age_min: actor.playable_age_min,
        playable_age_max: actor.playable_age_max,
        secondary_playable_age_min: actor.secondary_playable_age_min ?? null,
        secondary_playable_age_max: actor.secondary_playable_age_max ?? null,
        skills: actor.skills,
        gender_identities: actor.gender_identities,
        gender_expression: actor.gender_expression ?? "",
        pronouns: actor.pronouns ?? "",
        ethnicities: actor.ethnicities,
        racial_identities: actor.racial_identities,
        nationalities: actor.nationalities,
        languages: actor.languages,
        accents: actor.accents,
        disability_identities: actor.disability_identities,
        accessibility_notes: actor.accessibility_notes ?? "",
        demographic_notes: actor.demographic_notes ?? "",
        notes: actor.notes ?? "",
        skillsText: joinList(actor.skills),
        genderIdentitiesText: joinList(actor.gender_identities),
        ethnicitiesText: joinList(actor.ethnicities),
        racialIdentitiesText: joinList(actor.racial_identities),
        nationalitiesText: joinList(actor.nationalities),
        languagesText: joinList(actor.languages),
        accentsText: joinList(actor.accents),
        disabilityIdentitiesText: joinList(actor.disability_identities),
        includedRoleTypesText: joinList(actor.included_role_types?.length ? actor.included_role_types : defaultIncludedRoleTypes),
        excludedRoleTypesText: joinList(actor.excluded_role_types?.length ? actor.excluded_role_types : defaultExcludedRoleTypes)
      });
      setProfileFormOpen(false);
    }
  }, [actor]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setProfileMessage(null);
    setProfileError(null);
    if (form.playable_age_min > form.playable_age_max) {
      setProfileError("Playable age minimum must be less than or equal to playable age maximum.");
      return;
    }
    if (
      form.secondary_playable_age_min !== null &&
      form.secondary_playable_age_max !== null &&
      form.secondary_playable_age_min > form.secondary_playable_age_max
    ) {
      setProfileError("Secondary playable age minimum must be less than or equal to secondary playable age maximum.");
      return;
    }
    setSaving(true);
    try {
      await actorMutation.mutateAsync({
        name: form.name.trim(),
        sag_status: form.sag_status.trim(),
        union_status: form.union_status.trim(),
        current_location: form.current_location.trim(),
        playable_age_min: form.playable_age_min,
        playable_age_max: form.playable_age_max,
        secondary_playable_age_min: form.secondary_playable_age_min,
        secondary_playable_age_max: form.secondary_playable_age_max,
        skills: splitList(form.skillsText),
        gender_identities: splitList(form.genderIdentitiesText),
        gender_expression: form.gender_expression.trim() || null,
        pronouns: form.pronouns.trim() || null,
        ethnicities: splitList(form.ethnicitiesText),
        racial_identities: splitList(form.racialIdentitiesText),
        nationalities: splitList(form.nationalitiesText),
        languages: splitList(form.languagesText),
        accents: splitList(form.accentsText),
        disability_identities: splitList(form.disabilityIdentitiesText),
        included_role_types: splitList(form.includedRoleTypesText),
        excluded_role_types: splitList(form.excludedRoleTypesText),
        accessibility_notes: form.accessibility_notes.trim() || null,
        demographic_notes: form.demographic_notes.trim() || null,
        notes: form.notes.trim() || null
      });
      setProfileMessage("Actor profile saved.");
      setProfileFormOpen(false);
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Could not save actor profile.");
    } finally {
      setSaving(false);
    }
  }

  async function createRepresentation(event: FormEvent) {
    event.preventDefault();
    if (!actor) return;
    setRepresentationSaving(true);
    setRepresentationMessage(null);
    setRepresentationError(null);
    try {
      const payload = {
        actor_profile_id: actor.id,
        agency_name: representationForm.agency_name.trim(),
        agent_name: representationForm.agent_name.trim() || null,
        agent_email: representationForm.agent_email.trim() || null,
        agent_phone: representationForm.agent_phone.trim() || null,
        agency_website: representationForm.agency_website.trim() || null,
        representation_type: representationForm.representation_type,
        market: splitList(representationForm.market),
        notes: representationForm.notes.trim() || null,
        active: representationForm.active,
        start_date: representationForm.start_date || null,
        end_date: representationForm.end_date || null
      };
      const saved = editingRepresentationId
        ? await updateRepresentationMutation.mutateAsync({ id: editingRepresentationId, patch: payload })
        : await createRepresentationMutation.mutateAsync(payload);
      resetRepresentationForm();
      setRepresentationFormOpen(false);
      setEditingRepresentationId(null);
      setRepresentationMessage(`Saved ${saved.agency_name}.`);
    } catch (error) {
      setRepresentationError(error instanceof Error ? error.message : "Could not save representation.");
    } finally {
      setRepresentationSaving(false);
    }
  }

  function resetRepresentationForm() {
    setRepresentationForm({
      agency_name: "",
      agent_name: "",
      agent_email: "",
      agent_phone: "",
      agency_website: "",
      representation_type: "Theatrical",
      market: "",
      notes: "",
      active: true,
      start_date: "",
      end_date: ""
    });
  }

  function openNewRepresentationForm() {
    resetRepresentationForm();
    setEditingRepresentationId(null);
    setRepresentationMessage(null);
    setRepresentationError(null);
    setRepresentationFormOpen((current) => !current);
  }

  function openEditRepresentationForm(representation: Representation) {
    setRepresentationForm({
      agency_name: representation.agency_name,
      agent_name: representation.agent_name ?? "",
      agent_email: representation.agent_email ?? "",
      agent_phone: representation.agent_phone ?? "",
      agency_website: representation.agency_website ?? "",
      representation_type: representation.representation_type,
      market: joinList(representation.market),
      notes: representation.notes ?? "",
      active: representation.active,
      start_date: representation.start_date ?? "",
      end_date: representation.end_date ?? ""
    });
    setEditingRepresentationId(representation.id);
    setRepresentationMessage(null);
    setRepresentationError(null);
    setRepresentationFormOpen(true);
  }

  const activeRepresentations = representations.filter((item) => item.active);

  return (
    <Section title="Actor Profile" actions={<UserRound className="h-5 w-5 text-slate-500" />}>
      <div className="mb-4 rounded-md border border-slate-200 p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="font-semibold">Saved Profile</h3>
          <Button variant="secondary" onClick={() => setProfileFormOpen((current) => !current)}>
            {actor ? (profileFormOpen ? "Hide Profile Form" : "Edit Actor Profile") : (profileFormOpen ? "Hide Profile Form" : "Add New Actor Profile")}
          </Button>
        </div>
        {!actor ? (
          <p className="mt-2 text-sm text-slate-500">No actor profile has been saved yet.</p>
        ) : (
          <div className="mt-3 grid gap-3 text-sm md:grid-cols-2">
            <SavedField label="Name" value={actor.name} />
            <SavedField label="Current Location" value={actor.current_location} />
            <SavedField label="SAG Status" value={actor.sag_status} />
            <SavedField label="Union Status" value={actor.union_status} />
            <SavedField label="Playable Age Range" value={`${actor.playable_age_min}-${actor.playable_age_max}`} />
            <SavedField
              label="Secondary Playable Age Range"
              value={
                actor.secondary_playable_age_min !== null && actor.secondary_playable_age_min !== undefined &&
                actor.secondary_playable_age_max !== null && actor.secondary_playable_age_max !== undefined
                  ? `${actor.secondary_playable_age_min}-${actor.secondary_playable_age_max}`
                  : "Not listed"
              }
            />
            <SavedField label="Gender Identity" value={actor.gender_identities.length ? actor.gender_identities.join(", ") : "Not listed"} />
            <SavedField label="Gender Expression" value={actor.gender_expression || "Not listed"} />
            <SavedField label="Pronouns" value={actor.pronouns || "Not listed"} />
            <SavedField label="Ethnicity" value={actor.ethnicities.length ? actor.ethnicities.join(", ") : "Not listed"} />
            <SavedField label="Race" value={actor.racial_identities.length ? actor.racial_identities.join(", ") : "Not listed"} />
            <SavedField label="Nationality / Cultural Background" value={actor.nationalities.length ? actor.nationalities.join(", ") : "Not listed"} />
            <SavedField label="Languages" value={actor.languages.length ? actor.languages.join(", ") : "Not listed"} />
            <SavedField label="Accents" value={actor.accents.length ? actor.accents.join(", ") : "Not listed"} />
            <SavedField label="Disability Identity" value={actor.disability_identities.length ? actor.disability_identities.join(", ") : "Not listed"} />
            <SavedField label="Included Role Types" value={actor.included_role_types?.length ? actor.included_role_types.join(", ") : defaultIncludedRoleTypes.join(", ")} />
            <SavedField label="Excluded Role Types" value={actor.excluded_role_types?.length ? actor.excluded_role_types.join(", ") : defaultExcludedRoleTypes.join(", ")} />
            <SavedField label="Accessibility Notes" value={actor.accessibility_notes || "Not listed"} />
            <SavedField label="Demographic Notes" value={actor.demographic_notes || "Not listed"} />
            <SavedField label="Skills" value={actor.skills.length ? actor.skills.join(", ") : "Not listed"} />
            <SavedField label="Notes" value={actor.notes || "Not listed"} />
            <SavedField label="Last Updated" value={new Date(actor.updated_at).toLocaleString()} />
          </div>
        )}
      </div>
      {profileMessage && (
        <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
          {profileMessage}
        </div>
      )}
      {profileFormOpen && (
        <form className="grid gap-3" onSubmit={submit}>
          {profileError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {profileError}
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-2">
            <Field label="Name">
              <input className={inputClass} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </Field>
            <Field label="Current Location">
              <input className={inputClass} value={form.current_location} onChange={(e) => setForm({ ...form, current_location: e.target.value })} required />
            </Field>
            <Field label="SAG Status">
              <input className={inputClass} value={form.sag_status} onChange={(e) => setForm({ ...form, sag_status: e.target.value })} required />
            </Field>
            <Field label="Union Status">
              <input className={inputClass} value={form.union_status} onChange={(e) => setForm({ ...form, union_status: e.target.value })} required />
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-4">
            <Field label="Playable Min">
              <input className={inputClass} type="number" value={form.playable_age_min} onChange={(e) => setForm({ ...form, playable_age_min: Number(e.target.value) })} required />
            </Field>
            <Field label="Playable Max">
              <input className={inputClass} type="number" value={form.playable_age_max} onChange={(e) => setForm({ ...form, playable_age_max: Number(e.target.value) })} required />
            </Field>
            <Field label="Secondary Min">
              <input className={inputClass} type="number" value={form.secondary_playable_age_min ?? ""} onChange={(e) => setForm({ ...form, secondary_playable_age_min: e.target.value ? Number(e.target.value) : null })} />
            </Field>
            <Field label="Secondary Max">
              <input className={inputClass} type="number" value={form.secondary_playable_age_max ?? ""} onChange={(e) => setForm({ ...form, secondary_playable_age_max: e.target.value ? Number(e.target.value) : null })} />
            </Field>
          </div>
          <Field label="Skills">
            <input className={inputClass} value={form.skillsText} onChange={(e) => setForm({ ...form, skillsText: e.target.value })} />
          </Field>
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <h4 className="mb-2 text-sm font-semibold text-slate-800">Demographics For Breakdown Matching</h4>
            <p className="mb-3 text-xs text-slate-500">
              These fields are only used to compare your saved profile against explicit breakdown requirements. Leave anything blank that you do not want the app to use.
            </p>
            <div className="grid gap-3 md:grid-cols-2">
              <DemographicOptionPicker
                label="Gender Identity"
                options={genderIdentityOptions}
                value={splitList(form.genderIdentitiesText)}
                onChange={(value) => setForm({ ...form, genderIdentitiesText: joinList(value) })}
                customPlaceholder="Add a gender identity"
              />
              <DemographicOptionPicker
                label="Gender Expression"
                options={genderExpressionOptions}
                value={splitList(form.gender_expression)}
                onChange={(value) => setForm({ ...form, gender_expression: joinList(value) })}
                helpText="Use one or more if your casting range is flexible."
                customPlaceholder="Add a gender expression"
              />
              <DemographicOptionPicker
                label="Pronouns"
                options={pronounOptions}
                value={splitList(form.pronouns)}
                onChange={(value) => setForm({ ...form, pronouns: joinList(value) })}
                customPlaceholder="Add pronouns"
              />
              <DemographicOptionPicker
                label="Ethnicity"
                options={ethnicityOptions}
                value={splitList(form.ethnicitiesText)}
                onChange={(value) => setForm({ ...form, ethnicitiesText: joinList(value) })}
                customPlaceholder="Add an ethnicity"
              />
              <DemographicOptionPicker
                label="Race"
                options={raceIdentityOptions}
                value={splitList(form.racialIdentitiesText)}
                onChange={(value) => setForm({ ...form, racialIdentitiesText: joinList(value) })}
                customPlaceholder="Add a race identity"
              />
              <DemographicOptionPicker
                label="Nationality / Cultural Background"
                options={nationalityOptions}
                value={splitList(form.nationalitiesText)}
                onChange={(value) => setForm({ ...form, nationalitiesText: joinList(value) })}
                customPlaceholder="Add a nationality or cultural background"
              />
              <DemographicOptionPicker
                label="Languages"
                options={languageOptions}
                value={splitList(form.languagesText)}
                onChange={(value) => setForm({ ...form, languagesText: joinList(value) })}
                helpText="Used when a breakdown asks for a language."
                customPlaceholder="Add a language"
              />
              <DemographicOptionPicker
                label="Accents"
                options={accentOptions}
                value={splitList(form.accentsText)}
                onChange={(value) => setForm({ ...form, accentsText: joinList(value) })}
                helpText="Used when a breakdown asks for an accent or dialect."
                customPlaceholder="Add an accent"
              />
              <DemographicOptionPicker
                label="Disability Identity"
                options={disabilityIdentityOptions}
                value={splitList(form.disabilityIdentitiesText)}
                onChange={(value) => setForm({ ...form, disabilityIdentitiesText: joinList(value) })}
                helpText="Only add values you want the app to use for matching."
                customPlaceholder="Add a disability identity"
              />
              <DemographicOptionPicker
                label="Included Role Types"
                options={roleTypePreferenceOptions}
                value={splitList(form.includedRoleTypesText)}
                onChange={(value) => setForm({ ...form, includedRoleTypesText: joinList(value) })}
                helpText="These role types are treated as normally worth showing."
                customPlaceholder="Add included role type"
              />
              <DemographicOptionPicker
                label="Excluded Role Types"
                options={roleTypePreferenceOptions}
                value={splitList(form.excludedRoleTypesText)}
                onChange={(value) => setForm({ ...form, excludedRoleTypesText: joinList(value) })}
                helpText="These are hidden from normal breakdown views unless you remove them later."
                customPlaceholder="Add excluded role type"
              />
              <Field label="Accessibility Notes">
                <textarea className={inputClass} value={form.accessibility_notes} onChange={(e) => setForm({ ...form, accessibility_notes: e.target.value })} />
              </Field>
            </div>
            <Field label="Demographic Notes">
              <textarea className={inputClass} value={form.demographic_notes} onChange={(e) => setForm({ ...form, demographic_notes: e.target.value })} placeholder="Anything casting-fit related you want the app to remember." />
            </Field>
          </div>
          <Field label="Notes">
            <textarea className={inputClass} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </Field>
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={saving}>{saving ? "Saving..." : "Save Profile"}</Button>
            <Button variant="secondary" onClick={() => setProfileFormOpen(false)}>Cancel</Button>
          </div>
        </form>
      )}
      <div className="mt-4 rounded-md border border-slate-200 p-3">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="font-semibold">Represented By</h3>
          <Button variant="secondary" onClick={openNewRepresentationForm}>
            {representationFormOpen && !editingRepresentationId ? "Hide Representation Form" : "Add Representation"}
          </Button>
        </div>
        <div className="mt-3 grid gap-2 text-sm">
          {activeRepresentations.length === 0 ? (
            <p className="text-slate-500">No active representation added yet.</p>
          ) : activeRepresentations.map((representation) => (
            <div key={representation.id} className="rounded bg-slate-50 p-2">
              <p className="font-semibold">Represented by {representation.agency_name}</p>
              <div className="mt-2 grid gap-2 md:grid-cols-2">
                <SavedField label="Agent" value={representation.agent_name || "Not listed"} />
                <SavedField label="Type" value={representation.representation_type} />
                <SavedField label="Agent Email" value={representation.agent_email || "Not listed"} />
                <SavedField label="Agent Phone" value={representation.agent_phone || "Not listed"} />
                <SavedField label="Agency Website" value={representation.agency_website || "Not listed"} />
                <SavedField label="Markets" value={representation.market.join(", ") || "Not listed"} />
                <SavedField label="Start Date" value={representation.start_date || "Not listed"} />
                <SavedField label="End Date" value={representation.end_date || "Not listed"} />
                <SavedField label="Status" value={representation.active ? "Active" : "Inactive"} />
                <SavedField label="Notes" value={representation.notes || "Not listed"} />
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                <Button variant="secondary" onClick={() => openEditRepresentationForm(representation)}>Edit</Button>
                <Button variant="secondary" onClick={async () => {
                  await updateRepresentationMutation.mutateAsync({ id: representation.id, patch: { active: false, end_date: new Date().toISOString().slice(0, 10) } });
                }}>Mark Inactive</Button>
                <Button variant="danger" onClick={() => void deleteRepresentationMutation.mutateAsync(representation.id)}>Delete</Button>
              </div>
            </div>
          ))}
        </div>
        {representationFormOpen && <form className="mt-4 grid gap-3 md:grid-cols-2" onSubmit={createRepresentation}>
          {!actor && <p className="text-sm text-red-700 md:col-span-2">Create an actor profile before adding representation.</p>}
          {representationMessage && (
            <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700 md:col-span-2">
              {representationMessage}
            </p>
          )}
          {representationError && (
            <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 md:col-span-2">
              {representationError}
            </p>
          )}
          <Field label="Agency Name">
            <input className={inputClass} value={representationForm.agency_name} onChange={(e) => setRepresentationForm({ ...representationForm, agency_name: e.target.value })} required />
          </Field>
          <Field label="Agent Name">
            <input className={inputClass} value={representationForm.agent_name} onChange={(e) => setRepresentationForm({ ...representationForm, agent_name: e.target.value })} />
          </Field>
          <Field label="Agent Email">
            <input className={inputClass} type="email" value={representationForm.agent_email} onChange={(e) => setRepresentationForm({ ...representationForm, agent_email: e.target.value })} />
          </Field>
          <Field label="Agent Phone">
            <input className={inputClass} value={representationForm.agent_phone} onChange={(e) => setRepresentationForm({ ...representationForm, agent_phone: e.target.value })} />
          </Field>
          <Field label="Agency Website">
            <input className={inputClass} type="url" value={representationForm.agency_website} onChange={(e) => setRepresentationForm({ ...representationForm, agency_website: e.target.value })} />
          </Field>
          <Field label="Type">
            <select className={inputClass} value={representationForm.representation_type} onChange={(e) => setRepresentationForm({ ...representationForm, representation_type: e.target.value as Representation["representation_type"] })}>
              {representationTypes.map((type) => <option key={type}>{type}</option>)}
            </select>
          </Field>
          <Field label="Markets">
            <input className={inputClass} value={representationForm.market} onChange={(e) => setRepresentationForm({ ...representationForm, market: e.target.value })} placeholder="Los Angeles, Atlanta" />
          </Field>
          <Field label="Start Date">
            <input className={inputClass} type="date" value={representationForm.start_date} onChange={(e) => setRepresentationForm({ ...representationForm, start_date: e.target.value })} />
          </Field>
          <div className="md:col-span-2">
            <Field label="Notes">
              <textarea className={inputClass} value={representationForm.notes} onChange={(e) => setRepresentationForm({ ...representationForm, notes: e.target.value })} />
            </Field>
          </div>
          <div className="flex flex-wrap gap-2 md:col-span-2">
            <Button type="submit" disabled={!actor || representationSaving}>{representationSaving ? "Saving..." : editingRepresentationId ? "Save Representation" : "Add Representation"}</Button>
            <Button variant="secondary" onClick={() => {
              resetRepresentationForm();
              setEditingRepresentationId(null);
              setRepresentationFormOpen(false);
            }}>Cancel</Button>
          </div>
        </form>}
      </div>
    </Section>
  );
}
