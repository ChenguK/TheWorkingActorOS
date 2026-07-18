import { SourceLibraryPanel, useSourceResearchItems } from "../../source-library";
import { AutomationDashboard } from "./BreakdownDiscovery";
import { OpportunityManager } from "./BreakdownManager";
import { MergedAuditionReadinessPanel } from "./BreakdownReadiness";
import { useActorProfile, useRepresentations } from "../../profile";
import { useMaterials } from "../../materials";
import { useAuditionReadiness, useBreakdownRecommendations, useBreakdowns, useDiscoveryPlugins, useHiddenBreakdowns, useSubmissionQueue } from "../hooks/useBreakdownQueries";
import { useSystemCapabilities } from "../../../services/system";

export function BreakdownsPanel() {
  const capabilities = useSystemCapabilities();
  const sourceResearchItems = useSourceResearchItems();
  const actor = useActorProfile();
  const representations = useRepresentations();
  const materials = useMaterials(); const opportunities = useBreakdowns(); const hidden = useHiddenBreakdowns();
  const recommendations = useBreakdownRecommendations(); const plugins = useDiscoveryPlugins(); const queue = useSubmissionQueue(); const readiness = useAuditionReadiness();
  const queries = [["breakdowns", opportunities], ["hidden breakdowns", hidden], ["recommendations", recommendations], ["discovery plugins", plugins], ["submission queue", queue], ["readiness", readiness]] as const;
  return (
    <div className="grid gap-4">
      {queries.filter(([, query]) => query.isLoading).map(([label]) => <p key={label} role="status" className="text-sm text-slate-600">Loading {label}...</p>)}
      {queries.filter(([, query]) => query.isError).map(([label]) => <p key={label} role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">Could not load {label}. Other Breakdowns sections remain available.</p>)}
      <OpportunityManager
        opportunities={opportunities.data ?? []}
        hiddenOpportunities={hidden.data ?? []}
        representations={representations.data ?? []}
      />
      <MergedAuditionReadinessPanel
        actor={actor.data ?? null}
        opportunities={[...(opportunities.data ?? []), ...(hidden.data ?? [])]}
        recommendations={recommendations.data ?? []}
        assets={materials.data ?? []}
        readiness={readiness.data ?? []}
      />
      <SourceLibraryPanel />
      <AutomationDashboard
        plugins={plugins.data ?? []}
        hiddenOpportunities={hidden.data ?? []}
        recommendations={recommendations.data ?? []}
        queueItems={queue.data ?? []}
        opportunities={opportunities.data ?? []}
        sourceResearchItems={sourceResearchItems.data ?? []}
        capabilities={capabilities.data ?? null}
      />
    </div>
  );
}
