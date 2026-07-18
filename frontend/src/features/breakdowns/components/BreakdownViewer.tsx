import { useState, type ReactNode } from "react";
import { Badge } from "../../../components/ui";
import { sourceTypeLabel } from "../constants";
import type { BreakdownSection, Opportunity } from "../types";
import {
  FactInferencePanel,
  TextAction,
  boolLabel,
  detailValue,
  isTheaterBreakdown,
  parseConfidence,
  preparationText,
  productionFallback
} from "./BreakdownDetails";
import { RoleViewer } from "./BreakdownRoleDetails";

type BreakdownViewerSectionId =
  | "production"
  | "audition"
  | "preparation"
  | "roles"
  | "submission"
  | "location"
  | "source";

export function BreakdownViewer({
  opportunity,
  onRunDeepParse,
  onPasteText,
  onManualAddRole,
  deepParsePending = false
}: {
  opportunity: Opportunity;
  onRunDeepParse: () => Promise<void>;
  onPasteText: () => void;
  onManualAddRole: () => void | Promise<void>;
  deepParsePending?: boolean;
}) {
  const sections = breakdownViewerSections(opportunity);
  const [selectedId, setSelectedId] = useState<BreakdownViewerSectionId>(sections[0]?.id ?? "production");
  const selected = sections.find((section) => section.id === selectedId) ?? sections[0];
  const confidence = parsingConfidence(opportunity);

  return (
    <div className="grid gap-3">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {confidence.map((item) => (
          <div key={item.label} className="rounded border border-slate-200 bg-white p-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{item.label}</p>
            <p className={item.value < 70 ? "font-semibold text-amber-700" : "font-semibold text-emerald-700"}>{item.value}%</p>
          </div>
        ))}
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        <div className="rounded border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <h4 className="font-semibold text-ink">Original Breakdown Text</h4>
            {selected && <Badge>{selected.label}</Badge>}
          </div>
          <HighlightedBreakdownText text={opportunity.description} highlight={selected?.highlightText ?? ""} />
        </div>
        <div className="rounded border border-slate-200 bg-white p-3">
          <h4 className="mb-2 font-semibold text-ink">Parsed Structured Data</h4>
          <div className="mb-3 flex flex-wrap gap-2">
            {sections.map((section) => (
              <button
                key={section.id}
                type="button"
                className={`rounded px-2 py-1 text-xs font-medium ${
                  selectedId === section.id ? "bg-ink text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
                }`}
                onClick={() => setSelectedId(section.id)}
              >
                {section.label} · {section.confidence}%
              </button>
            ))}
          </div>
          {selected ? selected.content : <p className="text-slate-500">Select a parsed section to inspect it.</p>}
          {opportunity.breakdown_roles.length === 0 && (
            <div className="mt-3 grid gap-2 rounded bg-amber-50 p-3 text-amber-900">
              <p className="font-medium">The parser could not confidently identify individual role sections.</p>
              <div className="flex flex-wrap gap-2">
                <TextAction
                  onClick={onRunDeepParse}
                  disabled={deepParsePending}
                  ariaDescribedBy={`deep-parse-feedback-${opportunity.id}`}
                >Run deep parse</TextAction>
                <TextAction onClick={onPasteText}>Paste actual text</TextAction>
                <TextAction onClick={onManualAddRole}>Manually add role</TextAction>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HighlightedBreakdownText({ text, highlight }: { text: string; highlight: string }) {
  const normalizedHighlight = highlight.trim();
  if (!normalizedHighlight) {
    return <pre className="max-h-96 whitespace-pre-wrap overflow-auto rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">{text}</pre>;
  }
  const index = text.toLowerCase().indexOf(normalizedHighlight.toLowerCase());
  if (index < 0) {
    return (
      <pre className="max-h-96 whitespace-pre-wrap overflow-auto rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
        {text}
      </pre>
    );
  }
  const before = text.slice(0, index);
  const match = text.slice(index, index + normalizedHighlight.length);
  const after = text.slice(index + normalizedHighlight.length);
  return (
    <pre className="max-h-96 whitespace-pre-wrap overflow-auto rounded bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
      {before}
      <mark className="rounded bg-amber-200 px-1 text-ink">{match}</mark>
      {after}
    </pre>
  );
}

function breakdownViewerSections(opportunity: Opportunity): Array<{
  id: BreakdownViewerSectionId;
  label: string;
  confidence: number;
  highlightText: string;
  content: ReactNode;
}> {
  const byType = (types: string[]) => opportunity.breakdown_sections.filter((section) => types.includes(section.section_type));
  const roleHighlight = opportunity.breakdown_roles[0]?.role_notes || sectionHighlight(byType(["Roles", "Character Descriptions"]));
  return [
    {
      id: "production", label: "Production Details", confidence: fieldConfidence(opportunity, "project"),
      highlightText: sectionHighlight(byType(["Production Details"])) || String(opportunity.project ?? ""),
      content: <FactInferencePanel facts={(opportunity.extracted_facts?.production_details as Record<string, unknown> | undefined) ?? opportunity.production_details} inference={pickInference(opportunity.ai_inference, ["project_type", "breakdown_classification"])} fallbackFacts={productionFallback(opportunity)} />
    },
    {
      id: "audition", label: "Audition Information", confidence: fieldConfidence(opportunity, "audition"),
      highlightText: sectionHighlight(byType(["Audition Information", "Dates"])) || String(opportunity.audition_type ?? ""),
      content: <FactInferencePanel facts={(opportunity.extracted_facts?.audition_information as Record<string, unknown> | undefined) ?? {
        audition_type: opportunity.audition_type,
        audition_subtype: opportunity.role_details?.audition_subtype,
        audition_date: opportunity.production_details?.audition_date || opportunity.role_details?.audition_date,
        audition_time: opportunity.production_details?.audition_time || opportunity.role_details?.audition_time,
        audition_location: opportunity.audition_location || opportunity.production_details?.audition_location_name || opportunity.role_details?.audition_location_name,
        audition_address: opportunity.production_details?.audition_address || opportunity.role_details?.audition_address,
        callback_info: opportunity.role_details?.callback_info
      }} inference={{}} />
    },
    {
      id: "preparation", label: "Preparation", confidence: fieldConfidence(opportunity, "preparation"),
      highlightText: sectionHighlight(byType(["Preparation"])) || preparationText(opportunity),
      content: <FactInferencePanel facts={{ preparation: preparationText(opportunity) }} inference={{}} />
    },
    {
      id: "roles", label: "Role & Character Information", confidence: fieldConfidence(opportunity, "roles"),
      highlightText: roleHighlight, content: <RoleViewer roles={opportunity.breakdown_roles} />
    },
    {
      id: "submission", label: "Submission Instructions", confidence: fieldConfidence(opportunity, "submission"),
      highlightText: sectionHighlight(byType(["Submission Instructions"])),
      content: <FactInferencePanel facts={{ submission_instructions: detailValue(opportunity.role_details?.submission_instructions) || detailValue(opportunity.source_metadata?.submission_instructions) }} inference={{}} />
    },
    {
      id: "location", label: "Travel / Location", confidence: fieldConfidence(opportunity, "location"),
      highlightText: sectionHighlight(byType(["Locations"])) || String(opportunity.location ?? ""),
      content: <FactInferencePanel facts={{
        performance_location: opportunity.production_details?.performance_location,
        audition_location: opportunity.audition_location || opportunity.production_details?.audition_location_name,
        audition_address: opportunity.production_details?.audition_address,
        rehearsal_location: opportunity.production_details?.rehearsal_location,
        shoot_location: isTheaterBreakdown(opportunity) ? null : opportunity.shoot_location || opportunity.location,
        audition_travel_hours: opportunity.audition_travel_hours,
        travel_covered: boolLabel(opportunity.travel_covered),
        housing_covered: boolLabel(opportunity.housing_covered)
      }} inference={{}} />
    },
    {
      id: "source", label: "Source Metadata", confidence: parseConfidence(opportunity),
      highlightText: String(opportunity.original_post_url ?? ""),
      content: <FactInferencePanel facts={opportunity.source_metadata} fallbackFacts={{
        source_type: sourceTypeLabel(opportunity.source_type),
        platform: opportunity.platform,
        source_url: opportunity.original_post_url,
        classification: opportunity.breakdown_classification,
        rejection_reason: opportunity.rejection_reason
      }} inference={{}} />
    }
  ];
}

function pickInference(source: Record<string, unknown> | null | undefined, keys: string[]): Record<string, unknown> {
  return Object.fromEntries(Object.entries(source ?? {}).filter(([key]) => keys.includes(key)));
}

function parsingConfidence(opportunity: Opportunity): Array<{ label: string; value: number }> {
  return [
    { label: "Project Title", value: fieldConfidence(opportunity, "project") },
    { label: "Audition Info", value: fieldConfidence(opportunity, "audition") },
    { label: "Preparation", value: fieldConfidence(opportunity, "preparation") },
    { label: "Role Extraction", value: fieldConfidence(opportunity, "roles") },
    { label: "Location", value: fieldConfidence(opportunity, "location") },
    { label: "Overall", value: parseConfidence(opportunity) }
  ];
}

function fieldConfidence(opportunity: Opportunity, field: "project" | "audition" | "preparation" | "roles" | "location" | "submission"): number {
  const sectionScore = (types: string[]) => {
    const matches = opportunity.breakdown_sections.filter((section) => types.includes(section.section_type));
    return matches.length === 0 ? 0 : Math.max(...matches.map((section) => section.confidence_score));
  };
  if (field === "project") return opportunity.production_details?.project_title || opportunity.project ? Math.max(70, sectionScore(["Production Details"])) : sectionScore(["Production Details"]);
  if (field === "audition") return opportunity.audition_type && opportunity.audition_type !== "Unknown" ? Math.max(70, sectionScore(["Audition Information", "Dates"])) : sectionScore(["Audition Information", "Dates"]);
  if (field === "preparation") return preparationText(opportunity) ? Math.max(75, sectionScore(["Preparation"])) : sectionScore(["Preparation"]);
  if (field === "roles") return opportunity.breakdown_roles.length ? Math.max(...opportunity.breakdown_roles.map((role) => role.confidence_score)) : sectionScore(["Roles", "Character Descriptions"]);
  if (field === "location") return opportunity.location || opportunity.audition_location || opportunity.production_details?.audition_location_name ? Math.max(70, sectionScore(["Locations"])) : sectionScore(["Locations"]);
  return detailValue(opportunity.role_details?.submission_instructions) || detailValue(opportunity.source_metadata?.submission_instructions) ? Math.max(70, sectionScore(["Submission Instructions"])) : sectionScore(["Submission Instructions"]);
}

function sectionHighlight(sections: BreakdownSection[]): string {
  return sections.map((section) => section.raw_text).filter(Boolean).join("\n\n");
}
