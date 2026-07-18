import { UserRound } from "lucide-react";
import { Section } from "../../../components/ui";
import { errorMessage } from "../../../services/api/errors";
import { useRelationshipEditor } from "../hooks/useRelationshipEditor";
import { useRelationshipAnalytics, useRelationships } from "../hooks/useRelationshipQueries";
import type {
  Opportunity,
  Representation,
  Submission
} from "../types";
import { CommunicationLogPanel } from "./CommunicationLogPanel";
import { RelationshipForm } from "./RelationshipForm";
import { RelationshipInsights } from "./RelationshipInsights";
import { RelationshipList } from "./RelationshipList";

export function RelationshipsPanel({
  representations,
  opportunities,
  submissions
}: {
  representations: Representation[];
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  const relationshipsQuery = useRelationships();
  const analyticsQuery = useRelationshipAnalytics();
  const relationshipEditor = useRelationshipEditor();
  const relationships = relationshipsQuery.data ?? [];

  if (relationshipsQuery.isLoading || analyticsQuery.isLoading) {
    return <div role="status" className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-600">Loading Relationships...</div>;
  }

  const queryError = relationshipsQuery.error && !relationshipsQuery.data
    ? errorMessage(relationshipsQuery.error, "Could not load Relationships.")
    : analyticsQuery.error && !analyticsQuery.data
      ? errorMessage(analyticsQuery.error, "Could not load relationship insights.")
      : null;
  if (queryError) return <div role="alert" className="rounded bg-red-50 p-3 text-sm text-red-800">{queryError}</div>;

  return (
    <div className="grid gap-4">
      <Section title="Relationship History" actions={<UserRound className="h-5 w-5 text-slate-500" />}>
        <div className="grid gap-4">
          {(relationshipsQuery.isRefetching || analyticsQuery.isRefetching) && <p role="status" className="text-xs text-slate-500">Refreshing Relationships...</p>}
          <RelationshipInsights relationshipAnalytics={analyticsQuery.data ?? null} />
          <RelationshipForm
            form={relationshipEditor.form}
            setForm={relationshipEditor.setForm}
            opportunities={opportunities}
            submissions={submissions}
            onSubmit={relationshipEditor.create}
            saving={relationshipEditor.saving}
            error={relationshipEditor.error}
            submitLabel="Add Relationship"
          />
          <RelationshipList
            relationships={relationships}
            opportunities={opportunities}
            submissions={submissions}
            onSave={relationshipEditor.save}
            onDelete={relationshipEditor.remove}
          />
        </div>
      </Section>
      <CommunicationLogPanel
        representations={representations}
        opportunities={opportunities}
        submissions={submissions}
      />
    </div>
  );
}
