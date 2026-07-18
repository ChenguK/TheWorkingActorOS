import { AssetLibrary } from "./AssetLibrary";
import { SelfTapeLibraryPanel } from "./SelfTapeLibraryPanel";
import type {
  ActorProfile,
  Opportunity,
  Submission,
  SystemCapabilities
} from "../types";

export function MaterialsPanel({
  actor,
  capabilities,
  opportunities,
  submissions,
}: {
  actor: ActorProfile | null;
  capabilities?: SystemCapabilities | null;
  opportunities: Opportunity[];
  submissions: Submission[];
}) {
  return (
    <div className="grid gap-4">
      <AssetLibrary actor={actor} capabilities={capabilities} />
      <SelfTapeLibraryPanel
        opportunities={opportunities}
        submissions={submissions}
      />
    </div>
  );
}
