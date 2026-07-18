import { JournalPanel } from "@/features/journal";
import { useCareerTasks } from "@/features/career-intelligence";
import { useMaterialOptions } from "@/features/materials";
import { useOpportunityOptions } from "@/features/breakdowns";
import { useSubmissions } from "@/features/auditions";

export function JournalPage() {
  const careerTasks = useCareerTasks();
  const materials = useMaterialOptions();
  const opportunities = useOpportunityOptions();
  const submissions = useSubmissions();
  return (
    <JournalPanel
      opportunities={opportunities.data ?? []}
      submissions={submissions.data ?? []}
      assets={materials.data ?? []}
      careerTasks={careerTasks.data ?? []}
    />
  );
}
