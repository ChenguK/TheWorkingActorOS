import { MaterialsPanel } from "@/features/materials";
import { useActorProfile } from "@/features/profile";
import { useBreakdowns } from "@/features/breakdowns";
import { useSubmissions } from "@/features/auditions";
import { useSystemCapabilities } from "@/services/system";

export function MaterialsPage() {
  const actor = useActorProfile();
  const opportunities = useBreakdowns();
  const submissions = useSubmissions();
  const capabilities = useSystemCapabilities();
  return (
    <MaterialsPanel
      actor={actor.data ?? null}
      capabilities={capabilities.data ?? null}
      opportunities={opportunities.data ?? []}
      submissions={submissions.data ?? []}
    />
  );
}
