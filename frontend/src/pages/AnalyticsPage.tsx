import { AnalyticsPanel } from "@/features/analytics";
import { useSubmissions } from "@/features/auditions";
import { useSystemCapabilities } from "@/services/system";

export function AnalyticsPage() {
  const submissions = useSubmissions();
  const capabilities = useSystemCapabilities();
  return <AnalyticsPanel submissions={submissions.data ?? []} capabilities={capabilities.data ?? null} />;
}
