import type { Opportunity, SubmissionFormState } from "../types";
export { formatDateTime } from "../../../utils/dateTime";

export function externalBreakdownUrl(opportunity: Opportunity): string | null {
  const metadataUrl = opportunity.source_metadata?.source_url ?? opportunity.source_metadata?.url ?? opportunity.source_metadata?.original_post_url;
  const sourceUrl = opportunity.original_post_url || (typeof metadataUrl === "string" ? metadataUrl : "");
  return sourceUrl.trim() || null;
}

export function sourceTypeLabel(type: Opportunity["source_type"] | string) {
  return type === "Platform Discovery" ? "Platform Breakdown" : type;
}

export function detailValue(value: unknown): string {
  if (value === null || value === undefined || value === "" || value === false) return "";
  if (Array.isArray(value)) return value.filter(Boolean).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  const text = String(value);
  if (/^https?:\/\//i.test(text)) return "Link saved";
  return text.replace(/https?:\/\/\S+/gi, "Link saved");
}

export function stringValue(value: unknown): string {
  return detailValue(value);
}

export function toDateTimeLocal(value?: string | null): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value.includes("T") ? value.slice(0, 16) : "";
  }
  const pad = (item: number) => String(item).padStart(2, "0");
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}T${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
}

export function preparationText(opportunity: Opportunity): string {
  const direct = detailValue(opportunity.role_details?.preparation) || detailValue(opportunity.production_details?.preparation);
  if (direct) return direct;
  const section = opportunity.breakdown_sections?.find((item) => item.section_type === "Preparation");
  return section?.raw_text ?? "";
}

export function auditionNotes(
  form: Pick<SubmissionFormState, "notes" | "tape_due_at" | "audition_date" | "audition_location" | "virtual_audition_link" | "self_tape_submission_link" | "preparation_instructions" | "submission_instructions">,
  opportunity?: Opportunity
): string {
  return [
    form.notes,
    opportunity ? `Breakdown: ${opportunity.role} · ${opportunity.project}` : null,
    opportunity?.role_type ? `Role billing: ${opportunity.role_type}` : null,
    opportunity?.project_type ? `Project type: ${opportunity.project_type}` : null,
    opportunity?.union ? `Union: ${opportunity.union}` : null,
    opportunity?.source_type ? `Source: ${sourceTypeLabel(opportunity.source_type)}${opportunity.platform ? ` / ${opportunity.platform}` : ""}` : null,
    form.tape_due_at ? `Tape due: ${form.tape_due_at}` : null,
    form.audition_date ? `Audition date: ${form.audition_date}` : null,
    form.audition_location ? `Audition location: ${form.audition_location}` : null,
    form.virtual_audition_link ? `Virtual audition link: ${form.virtual_audition_link}` : null,
    form.self_tape_submission_link ? `Self-tape submission link: ${form.self_tape_submission_link}` : null,
    form.preparation_instructions ? `Preparation: ${form.preparation_instructions}` : null,
    form.submission_instructions ? `Submission instructions: ${form.submission_instructions}` : null,
    opportunity?.travel_covered !== undefined ? `Travel covered: ${opportunity.travel_covered ? "Yes" : "No"}` : null,
    opportunity?.housing_covered !== undefined ? `Housing covered: ${opportunity.housing_covered ? "Yes" : "No"}` : null
  ].filter(Boolean).join("\n");
}

export function parseAuditionText(text: string): Partial<SubmissionFormState> {
  const clean = text.trim();
  if (!clean) return {};
  const urlMatches = clean.match(/https?:\/\/[^\s)]+/gi) ?? [];
  const virtualLink = urlMatches.find((url) => /zoom|meet\.google|teams|webex|virtual/i.test(url)) ?? "";
  const submissionLink = urlMatches.find((url) => /form|airtable|casting|actorsaccess|castingnetworks|castingfrontier|upload|submit|self[-_]?tape/i.test(url)) ?? "";
  const tapeDue = firstLineMatch(clean, /(self[-\s]?tape|tape|submission)\s*(due|deadline)?\s*[:-]?\s*([^\n]+)/i, 3);
  const auditionDate = firstLineMatch(clean, /(audition|callback)\s*(date|time)?\s*[:-]?\s*([^\n]+)/i, 3);
  const location = firstLineMatch(clean, /(audition\s*)?location\s*[:-]?\s*([^\n]+)/i, 2);
  const preparation = blockAfterHeading(clean, ["preparation", "prep"]);
  const submission = blockAfterHeading(clean, ["submission instructions", "submission", "send to", "instructions"]);

  return {
    tape_due_at: toDateTimeLocal(tapeDue),
    audition_date: toDateTimeLocal(auditionDate),
    audition_location: location,
    virtual_audition_link: virtualLink,
    self_tape_submission_link: submissionLink,
    preparation_instructions: preparation,
    submission_instructions: submission,
    notes: `Parsed from pasted audition text:\n${clean}`
  };
}

function firstLineMatch(text: string, pattern: RegExp, group = 1): string {
  const match = text.match(pattern);
  return match?.[group]?.trim() ?? "";
}

function blockAfterHeading(text: string, headings: string[]): string {
  const headingPattern = headings.map((heading) => heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  const stopPattern = "project|role|location|audition|callback|preparation|prep|submission instructions|submission|send to|notes";
  const match = text.match(new RegExp(`(?:^|\\n)\\s*(?:${headingPattern})\\s*:?\\s*\\n?([\\s\\S]*?)(?=\\n\\s*(?:${stopPattern})\\s*:?\\s*\\n|$)`, "i"));
  return match?.[1]?.trim() ?? "";
}
