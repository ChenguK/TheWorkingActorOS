import { RelationshipsPanel } from "@/features/relationships";
import { useRepresentations } from "@/features/profile";
import { useBreakdowns } from "@/features/breakdowns";
import { useSubmissions } from "@/features/auditions";

export function RelationshipsPage() {
  const representations = useRepresentations();
  const opportunities = useBreakdowns();
  const submissions = useSubmissions();
  return (
    <RelationshipsPanel
      representations={representations.data ?? []}
      opportunities={opportunities.data ?? []}
      submissions={submissions.data ?? []}
    />
  );
}
