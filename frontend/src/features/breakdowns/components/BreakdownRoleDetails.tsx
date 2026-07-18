import { Badge } from "../../../components/ui";
import type { Opportunity } from "../types";
import { KeyValueEntries, detailValue } from "./BreakdownDetails";

export function RoleViewer({ roles }: { roles: Opportunity["breakdown_roles"] }) {
  if (roles.length === 0) {
    return <p className="text-slate-500">No individual roles are available yet.</p>;
  }
  return (
    <div className="grid gap-2">
      {roles.map((role) => (
        <div key={role.id} className="min-w-0 rounded bg-slate-50 p-2">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <p className="break-words font-semibold text-ink">{role.role_name}</p>
            {(role.billing || role.role_type || role.billing_or_role_type) && <Badge>{role.billing || role.role_type || role.billing_or_role_type}</Badge>}
            <Badge>{compatibilityLabel(role)}</Badge>
            <Badge>Confidence {role.confidence_score}%</Badge>
          </div>
          <div className="grid gap-3">
            <RoleInformationPanel role={role} />
            <CharacterInformationPanel role={role} />
            <CompatibilitySummary role={role} />
          </div>
        </div>
      ))}
    </div>
  );
}

function RoleInformationPanel({ role }: { role: Opportunity["breakdown_roles"][number] }) {
  const directFacts = {
    role_name: role.role_name,
    role_type: role.role_type,
    billing: role.billing || role.billing_or_role_type,
    union_status: role.union_status,
    gender_presentation: role.gender_presentation,
    ethnicity_or_cultural_background: role.ethnicity_or_cultural_background,
    playable_age: role.playable_age_min && role.playable_age_max ? `${role.playable_age_min}-${role.playable_age_max}` : null,
    height_requirements: role.height_requirements,
    vocal_requirements: role.vocal_requirements,
    dance_requirements: role.dance_requirements,
    movement_requirements: role.movement_requirements,
    language_requirements: role.language_requirements,
    special_skills: role.special_skills,
    preparation_notes: role.preparation_notes
  };
  const extractedFacts = role.extracted_facts ?? {};
  const roleFacts = {
    ...extractedFacts,
    ...Object.fromEntries(Object.entries(directFacts).filter(([, value]) => detailValue(value)))
  };
  delete (roleFacts as Record<string, unknown>).character_description;
  delete (roleFacts as Record<string, unknown>).character_traits;
  delete (roleFacts as Record<string, unknown>).archetypes;

  return (
    <section className="rounded border border-emerald-100 bg-emerald-50 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h5 className="font-semibold text-emerald-950">Role Information</h5>
        <Badge>From Breakdown</Badge>
      </div>
      <p className="mb-3 text-xs text-emerald-900">
        These are the production's stated casting requirements, preserved separately from AI interpretation.
      </p>
      {role.casting_language && (
        <div className="mb-3 rounded border border-emerald-100 bg-white p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h6 className="font-semibold text-ink">Casting shorthand</h6>
            <Badge>From Breakdown</Badge>
          </div>
          <KeyValueEntries
            entries={Object.entries({
              original_text: role.casting_language.original_text,
              billing: role.casting_language.billing,
              age_range: role.casting_language.age_range,
              gender: role.casting_language.gender,
              ethnicity: role.casting_language.ethnicity,
              union: role.casting_language.union,
              compensation: role.casting_language.compensation,
              special_notes: role.casting_language.special_notes
            }).filter(([, value]) => detailValue(value))}
          />
        </div>
      )}
      <KeyValueEntries entries={Object.entries(roleFacts).filter(([, value]) => detailValue(value))} />
    </section>
  );
}

function CharacterInformationPanel({ role }: { role: Opportunity["breakdown_roles"][number] }) {
  const characterFacts = {
    character_name: role.role_name,
    character_description: role.character_description,
    character_notes_from_breakdown: role.role_notes
  };
  const profile = role.character_profile;

  return (
    <section className="rounded border border-violet-100 bg-violet-50 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h5 className="font-semibold text-violet-950">Character Information</h5>
      </div>
      <div className="grid gap-3">
        <div className="rounded border border-violet-100 bg-white p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h6 className="font-semibold text-ink">From Breakdown</h6>
            <Badge>Original Character Text</Badge>
          </div>
          <KeyValueEntries entries={Object.entries(characterFacts).filter(([, value]) => detailValue(value))} />
        </div>
        <div className="rounded border border-violet-100 bg-white p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h6 className="font-semibold text-violet-950">AI Character Interpretation</h6>
            <Badge>Inferred from role description</Badge>
          </div>
          {profile ? (
            <>
              {profile.ai_summary && (
                <p className="mb-3 text-sm text-violet-950">{profile.ai_summary}</p>
              )}
              <KeyValueEntries
                entries={Object.entries({
                  primary_archetypes: profile.primary_archetypes,
                  secondary_archetypes: profile.secondary_archetypes,
                  archetype_confidence_scores: formatArchetypeScores(profile.archetype_confidence_scores),
                  personality_traits: profile.personality_traits,
                  emotional_traits: profile.emotional_traits,
                  relationships: profile.relationships,
                  motivations: profile.motivations,
                  internal_conflict: profile.internal_conflict,
                  external_conflict: profile.external_conflict,
                  emotional_arc: profile.emotional_arc,
                  genre: profile.genre,
                  tone_levels: `Comedy ${profile.comedic_level}% · Drama ${profile.dramatic_level}%`,
                  recommended_materials: profile.recommended_materials
                }).filter(([, value]) => detailValue(value))}
              />
            </>
          ) : (
            <p className="text-sm text-slate-600">No AI character interpretation has been generated yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function CompatibilitySummary({ role }: { role: Opportunity["breakdown_roles"][number] }) {
  return (
    <section className="rounded border border-slate-200 bg-white p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <h5 className="font-semibold text-ink">Role Fit</h5>
        <Badge>AI Recommendation</Badge>
      </div>
      <KeyValueEntries
        entries={Object.entries({
          recommendation: compatibilityLabel(role),
          fit_status: role.fit_status,
          explanation: role.fit_explanation
        }).filter(([, value]) => detailValue(value))}
      />
    </section>
  );
}

function compatibilityLabel(role: Opportunity["breakdown_roles"][number]): string {
  const compatibility = role.ai_inference?.compatibility;
  if (compatibility && typeof compatibility === "object" && "value" in compatibility) {
    const value = (compatibility as Record<string, unknown>).value;
    if (value) return String(value);
  }
  return {
    "Strong Fit": "Strong Match",
    "Possible Fit": "Good Match",
    "Stretch Fit": "Stretch",
    "Not Fit": "Not Recommended",
    "Needs Review": "Low Fit"
  }[role.fit_status] ?? role.fit_status;
}

function formatArchetypeScores(scores?: NonNullable<Opportunity["breakdown_roles"][number]["character_profile"]>["archetype_confidence_scores"]): string {
  if (!scores || scores.length === 0) return "";
  return scores
    .map((item) => `${item.archetype} (${item.confidence}% ${item.tier.toLowerCase()}${item.evidence?.length ? `: ${item.evidence.join(", ")}` : ""})`)
    .join("; ");
}
