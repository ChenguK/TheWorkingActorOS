import { AuditionsPanel } from "@/features/auditions";
import { useActorProfile } from "@/features/profile";
import { useBreakdowns } from "@/features/breakdowns";
import { useMaterialOptions } from "@/features/materials";

export function AuditionsPage() {
  const actor = useActorProfile();
  const opportunities = useBreakdowns();
  const materials = useMaterialOptions();
  return (
    <AuditionsPanel
      actor={actor.data ?? null}
      opportunities={opportunities.data ?? []}
      assets={materials.data ?? []}
    />
  );
}
