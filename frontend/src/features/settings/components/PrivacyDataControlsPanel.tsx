import { ShieldCheck } from "lucide-react";
import { EntitySummary, FieldGrid, Section } from "../../../components/ui";

export function PrivacyDataControlsPanel() {
  return (
    <Section title="Privacy & Data Controls" actions={<ShieldCheck className="h-5 w-5 text-slate-500" />}>
      <FieldGrid columns={3}>
        <EntitySummary title="Local Materials" subtitle="Uploaded headshots, reels, slates, resumes, and self-tapes are managed as local files by this application." />
        <EntitySummary title="Platform Boundaries" subtitle="Public profile imports and platform mappings stay user-triggered and draft-first. Protected casting platform media is not fetched automatically." />
        <EntitySummary title="Submission Approval" subtitle="Submission automation remains queued for review and requires approval before any execution step." />
      </FieldGrid>
    </Section>
  );
}
