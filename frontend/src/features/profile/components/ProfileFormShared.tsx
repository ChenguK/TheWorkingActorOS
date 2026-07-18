import { useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { Button, inputClass } from "../../../components/ui";
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
import { defaultExcludedRoleTypes, defaultIncludedRoleTypes } from "../../../constants/workflowOptions";
import { joinList } from "../../../utils/tags";
import type { ActingCreditCategory, PlatformImportMethod, PlatformName, Representation, TravelPreference } from "../../../types/domain";

export const platformNames: PlatformName[] = ["Actors Access", "Casting Networks", "Casting Frontier", "Other"];
export const platformImportMethods: PlatformImportMethod[] = [
  "Manual Copy/Paste",
  "Uploaded PDF",
  "Uploaded Screenshot",
  "Uploaded CSV",
  "User-Provided Text",
  "Manual Guided Form"
];
export const representationTypes: Representation["representation_type"][] = ["Theatrical", "Commercial", "Voiceover", "Print", "Manager", "Other"];
export const actingCreditCategories: ActingCreditCategory[] = ["Television", "Film", "Commercial", "Theater", "New Media", "Voiceover", "Industrial", "Print", "Training", "Special Skills", "Other"];
export const roleTypePreferenceOptions = [...defaultIncludedRoleTypes, ...defaultExcludedRoleTypes];

export type ActorProfileForm = {
  name: string;
  sag_status: string;
  union_status: string;
  current_location: string;
  playable_age_min: number;
  playable_age_max: number;
  secondary_playable_age_min: number | null;
  secondary_playable_age_max: number | null;
  skills: string[];
  gender_identities: string[];
  gender_expression: string;
  pronouns: string;
  ethnicities: string[];
  racial_identities: string[];
  nationalities: string[];
  languages: string[];
  accents: string[];
  disability_identities: string[];
  accessibility_notes: string;
  demographic_notes: string;
  notes: string;
  skillsText: string;
  genderIdentitiesText: string;
  ethnicitiesText: string;
  racialIdentitiesText: string;
  nationalitiesText: string;
  languagesText: string;
  accentsText: string;
  disabilityIdentitiesText: string;
  includedRoleTypesText: string;
  excludedRoleTypesText: string;
};

export const blankProfile: ActorProfileForm = {
  name: "",
  sag_status: "SAG-AFTRA",
  union_status: "SAG-AFTRA",
  current_location: "",
  playable_age_min: 30,
  playable_age_max: 45,
  secondary_playable_age_min: null,
  secondary_playable_age_max: null,
  skills: [],
  gender_identities: [],
  gender_expression: "",
  pronouns: "",
  ethnicities: [],
  racial_identities: [],
  nationalities: [],
  languages: [],
  accents: [],
  disability_identities: [],
  accessibility_notes: "",
  demographic_notes: "",
  notes: "",
  skillsText: "",
  genderIdentitiesText: "",
  ethnicitiesText: "",
  racialIdentitiesText: "",
  nationalitiesText: "",
  languagesText: "",
  accentsText: "",
  disabilityIdentitiesText: "",
  includedRoleTypesText: joinList(defaultIncludedRoleTypes),
  excludedRoleTypesText: joinList(defaultExcludedRoleTypes)
};

export const demographicOptionGroups = {
  accentOptions,
  disabilityIdentityOptions,
  ethnicityOptions,
  genderExpressionOptions,
  genderIdentityOptions,
  languageOptions,
  nationalityOptions,
  pronounOptions,
  raceIdentityOptions
};

export function SavedField({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded bg-white px-3 py-2">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 break-words text-sm text-ink">{value}</p>
    </div>
  );
}

export function DemographicOptionPicker({
  label,
  value,
  options,
  onChange,
  helpText,
  customPlaceholder = "Add a custom value"
}: {
  label: string;
  value: string[];
  options: string[];
  onChange: (value: string[]) => void;
  helpText?: string;
  customPlaceholder?: string;
}) {
  const [selectedOption, setSelectedOption] = useState("");
  const [customValue, setCustomValue] = useState("");
  const fieldId = "demographic_" + label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  const normalizedValue = value.map((item) => item.trim()).filter(Boolean);

  function addValue(item: string) {
    const cleaned = item.trim();
    if (!cleaned) return;
    const exists = normalizedValue.some((existing) => existing.toLowerCase() === cleaned.toLowerCase());
    if (!exists) onChange([...normalizedValue, cleaned]);
    setSelectedOption("");
    setCustomValue("");
  }

  function removeValue(item: string) {
    onChange(normalizedValue.filter((existing) => existing !== item));
  }

  return (
    <div className="grid gap-2 text-sm">
      <label className="grid gap-1 font-medium text-slate-700" htmlFor={fieldId + "_select"}>
        <span>{label}</span>
        <div className="flex flex-col gap-2 sm:flex-row">
          <select
            id={fieldId + "_select"}
            name={fieldId + "_select"}
            className={inputClass}
            value={selectedOption}
            onChange={(event) => {
              setSelectedOption(event.target.value);
              addValue(event.target.value);
            }}
          >
            <option value="">Choose an option</option>
            {options.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id={fieldId + "_custom"}
          name={fieldId + "_custom"}
          className={inputClass}
          value={customValue}
          onChange={(event) => setCustomValue(event.target.value)}
          placeholder={customPlaceholder}
        />
        <Button variant="secondary" onClick={() => addValue(customValue)}>Add</Button>
      </div>
      {helpText && <p className="text-xs text-slate-500">{helpText}</p>}
      <div className="flex min-h-8 flex-wrap gap-2">
        {normalizedValue.length === 0 ? <span className="text-xs text-slate-500">No values selected.</span> : normalizedValue.map((item) => (
          <span key={item} className="inline-flex items-center gap-1 rounded bg-white px-2 py-1 text-xs font-medium text-slate-700 ring-1 ring-slate-200">
            {item}
            <button type="button" className="rounded p-0.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800" onClick={() => removeValue(item)} aria-label={"Remove " + item}>
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}

export function minutesLabel(minutes: number) {
  const hours = minutes / 60;
  return Number.isInteger(hours) ? minutes + " minutes (" + hours + " hours)" : minutes + " minutes (" + hours.toFixed(1) + " hours)";
}

export function auditionTravelSummary(travel: TravelPreference) {
  const virtual = travel.audition_virtual_allowed ? "will consider virtual auditions" : "does not prefer virtual auditions";
  const selfTape = travel.audition_self_tape_allowed ? "will consider self-tape auditions" : "does not prefer self-tape auditions";
  return "For auditions, you are willing to drive up to " + minutesLabel(travel.audition_max_drive_time) + " for an in-person audition. You " + virtual + ", and you " + selfTape + ".";
}

export function workingAsLocalSummary(travel: TravelPreference) {
  const housing = travel.working_as_local_housing_self_provided
    ? "and you are willing to provide your own housing when you arrive"
    : "but you do not want to provide your own housing when you arrive";
  const beyond = travel.require_travel_housing_over_local_drive
    ? "Past that drive time, the job should provide travel and housing."
    : "Past that drive time, you want to review the travel and housing situation case by case.";
  return "For work you accept as a local hire, you are willing to drive up to " + minutesLabel(travel.working_as_local_drive_time) + " while covering your own travel " + housing + ". " + beyond;
}

export function coveredProductionTravelSummary(travel: TravelPreference) {
  const flights = travel.flight_allowed ? "You are open to flights if they are covered." : "You are not currently open to flights.";
  const housing = travel.housing_required ? "Housing is required for non-local work." : "Housing is not marked as required for non-local work.";
  const international = travel.international_allowed ? "You are open to international work." : "You are not currently open to international work.";
  return "For production travel that is covered, you are open to travel within " + minutesLabel(travel.extended_drive_time) + " by car. " + flights + " " + housing + " " + international;
}

