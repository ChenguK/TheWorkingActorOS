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
import { useSaveTravelPreferences } from "../hooks/useProfileQueries";
import { auditionTravelSummary, coveredProductionTravelSummary, minutesLabel, SavedField, workingAsLocalSummary } from "./ProfileFormShared";

export function TravelPreferencePanel({ actor, travel }: { actor: ActorProfile | null; travel: TravelPreference | null }) {
  const saveMutation = useSaveTravelPreferences(actor?.id);
  const [form, setForm] = useState({
    max_local_drive_time: 300,
    extended_drive_time: 720,
    flight_allowed: true,
    housing_required: false,
    international_allowed: false,
    audition_max_drive_time: 120,
    audition_virtual_allowed: true,
    audition_self_tape_allowed: true,
    working_as_local_drive_time: 300,
    working_as_local_housing_self_provided: true,
    require_travel_housing_over_local_drive: true,
    audition_notes: "",
    working_notes: ""
  });
  const [travelFormOpen, setTravelFormOpen] = useState(false);
  const [savingTravel, setSavingTravel] = useState(false);
  const [travelMessage, setTravelMessage] = useState<string | null>(null);
  const [travelError, setTravelError] = useState<string | null>(null);

  useEffect(() => {
    if (travel) {
      setForm({
        max_local_drive_time: travel.max_local_drive_time,
        extended_drive_time: travel.extended_drive_time,
        flight_allowed: travel.flight_allowed,
        housing_required: travel.housing_required,
        international_allowed: travel.international_allowed,
        audition_max_drive_time: travel.audition_max_drive_time,
        audition_virtual_allowed: travel.audition_virtual_allowed,
        audition_self_tape_allowed: travel.audition_self_tape_allowed,
        working_as_local_drive_time: travel.working_as_local_drive_time,
        working_as_local_housing_self_provided: travel.working_as_local_housing_self_provided,
        require_travel_housing_over_local_drive: travel.require_travel_housing_over_local_drive,
        audition_notes: travel.audition_notes ?? "",
        working_notes: travel.working_notes ?? ""
      });
      setTravelFormOpen(false);
    }
  }, [travel]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!actor) return;
    setTravelMessage(null);
    setTravelError(null);
    if (form.working_as_local_drive_time <= 0) {
      setTravelError("Working as local drive time must be greater than zero.");
      return;
    }
    if (form.extended_drive_time < form.working_as_local_drive_time) {
      setTravelError("Covered production travel drive time must be greater than or equal to the working-as-local drive time.");
      return;
    }
    if (form.audition_max_drive_time <= 0) {
      setTravelError("Audition max drive time must be greater than zero.");
      return;
    }
    setSavingTravel(true);
    try {
      await saveMutation.mutateAsync({
        ...form,
        actor_profile_id: actor.id,
        max_local_drive_time: form.working_as_local_drive_time,
        audition_notes: form.audition_notes.trim() || null,
        working_notes: form.working_notes.trim() || null
      });
      setTravelMessage("Travel preferences saved.");
      setTravelFormOpen(false);
    } catch (error) {
      setTravelError(error instanceof Error ? error.message : "Could not save travel preferences.");
    } finally {
      setSavingTravel(false);
    }
  }

  return (
    <Section title="Travel Preferences" actions={<MapPin className="h-5 w-5 text-slate-500" />}>
      {!actor ? <EmptyState>Create an actor profile before saving travel preferences.</EmptyState> : (
        <div className="grid gap-4">
          <div className="rounded-md border border-slate-200 p-3">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="font-semibold">Saved Travel Preferences</h3>
              <Button variant="secondary" onClick={() => setTravelFormOpen((current) => !current)}>
                {travel ? (travelFormOpen ? "Hide Travel Form" : "Edit Travel Preferences") : (travelFormOpen ? "Hide Travel Form" : "Add Travel Preferences")}
              </Button>
            </div>
            {!travel ? (
              <p className="mt-2 text-sm text-slate-500">No travel preferences have been saved yet.</p>
            ) : (
              <div className="mt-3 grid gap-4">
                <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-950">
                  <h4 className="font-semibold">Plain-English Summary</h4>
                  <div className="mt-2 grid gap-2">
                    <p>{auditionTravelSummary(travel)}</p>
                    <p>{workingAsLocalSummary(travel)}</p>
                    <p>{coveredProductionTravelSummary(travel)}</p>
                  </div>
                </div>
                <div className="grid gap-3 xl:grid-cols-3">
                  <div className="rounded bg-slate-50 p-3">
                    <h4 className="font-semibold">Audition Travel</h4>
                    <div className="mt-2 grid gap-2">
                      <SavedField label="Max In-Person Audition Drive Time" value={minutesLabel(travel.audition_max_drive_time)} />
                      <SavedField label="Virtual Auditions" value={travel.audition_virtual_allowed ? "Allowed" : "Not preferred"} />
                      <SavedField label="Self-Tape Auditions" value={travel.audition_self_tape_allowed ? "Allowed" : "Not preferred"} />
                      <SavedField label="Audition Notes" value={travel.audition_notes || "Not listed"} />
                    </div>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <h4 className="font-semibold">Working as Local</h4>
                    <div className="mt-2 grid gap-2">
                      <SavedField label="Max Drive Time When I Cover Travel/Housing" value={minutesLabel(travel.working_as_local_drive_time)} />
                      <SavedField label="I Provide My Own Housing In This Range" value={travel.working_as_local_housing_self_provided ? "Yes" : "No"} />
                      <SavedField label="Past This Drive Time" value={travel.require_travel_housing_over_local_drive ? "Require production-paid travel and housing" : "Open to review case by case"} />
                    </div>
                  </div>
                  <div className="rounded bg-slate-50 p-3">
                    <h4 className="font-semibold">Production Travel If Covered</h4>
                    <div className="mt-2 grid gap-2">
                      <SavedField label="Covered Drive Range" value={minutesLabel(travel.extended_drive_time)} />
                      <SavedField label="Flights" value={travel.flight_allowed ? "Allowed when covered" : "Not allowed"} />
                      <SavedField label="Housing Required" value={travel.housing_required ? "Yes" : "No"} />
                      <SavedField label="International Work" value={travel.international_allowed ? "Allowed" : "Not allowed"} />
                      <SavedField label="Working Notes" value={travel.working_notes || "Not listed"} />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {travelMessage && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
              {travelMessage}
            </div>
          )}

          {travelFormOpen && (
            <form className="grid gap-4" onSubmit={submit}>
              {travelError && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {travelError}
                </div>
              )}
              <div className="grid gap-3 xl:grid-cols-3">
                <div className="rounded-md border border-slate-200 p-3">
                  <h3 className="font-semibold">Audition Travel</h3>
                  <div className="mt-3 grid gap-3">
                    <Field label="Max In-Person Audition Drive Time (minutes)">
                      <input className={inputClass} type="number" value={form.audition_max_drive_time} onChange={(e) => setForm({ ...form, audition_max_drive_time: Number(e.target.value) })} />
                    </Field>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.audition_virtual_allowed} onChange={(e) => setForm({ ...form, audition_virtual_allowed: e.target.checked })} />
                      Virtual auditions allowed
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.audition_self_tape_allowed} onChange={(e) => setForm({ ...form, audition_self_tape_allowed: e.target.checked })} />
                      Self-tape auditions allowed
                    </label>
                    <Field label="Audition Travel Notes">
                      <textarea className={inputClass} value={form.audition_notes} onChange={(e) => setForm({ ...form, audition_notes: e.target.value })} />
                    </Field>
                  </div>
                </div>

                <div className="rounded-md border border-slate-200 p-3">
                  <h3 className="font-semibold">Working as Local</h3>
                  <div className="mt-3 grid gap-3">
                    <Field label="Max Drive Time When I Cover Travel/Housing (minutes)">
                      <input className={inputClass} type="number" value={form.working_as_local_drive_time} onChange={(e) => setForm({ ...form, working_as_local_drive_time: Number(e.target.value), max_local_drive_time: Number(e.target.value) })} />
                    </Field>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.working_as_local_housing_self_provided} onChange={(e) => setForm({ ...form, working_as_local_housing_self_provided: e.target.checked })} />
                      I will provide my own housing within this range
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.require_travel_housing_over_local_drive} onChange={(e) => setForm({ ...form, require_travel_housing_over_local_drive: e.target.checked, housing_required: e.target.checked })} />
                      Past this drive time, require production-paid travel and housing
                    </label>
                  </div>
                </div>

                <div className="rounded-md border border-slate-200 p-3">
                  <h3 className="font-semibold">Production Travel If Covered</h3>
                  <div className="mt-3 grid gap-3">
                    <Field label="Covered Drive Range (minutes)">
                      <input className={inputClass} type="number" value={form.extended_drive_time} onChange={(e) => setForm({ ...form, extended_drive_time: Number(e.target.value) })} />
                    </Field>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.flight_allowed} onChange={(e) => setForm({ ...form, flight_allowed: e.target.checked })} />
                      Flights allowed when covered
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.housing_required} onChange={(e) => setForm({ ...form, housing_required: e.target.checked })} />
                      Housing required beyond local range
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700">
                      <input type="checkbox" checked={form.international_allowed} onChange={(e) => setForm({ ...form, international_allowed: e.target.checked })} />
                      International work allowed
                    </label>
                    <Field label="Working Travel Notes">
                      <textarea className={inputClass} value={form.working_notes} onChange={(e) => setForm({ ...form, working_notes: e.target.value })} />
                    </Field>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={savingTravel}>{savingTravel ? "Saving..." : "Save Travel Preferences"}</Button>
                <Button variant="secondary" onClick={() => setTravelFormOpen(false)}>Cancel</Button>
              </div>
            </form>
          )}
        </div>
      )}
    </Section>
  );
}
