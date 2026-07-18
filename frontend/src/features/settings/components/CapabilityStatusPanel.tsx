import { SlidersHorizontal } from "lucide-react";
import { Button, CapabilityNotice, EmptyState, Section, StatusBadge } from "../../../components/ui";
import { useSystemCapabilities } from "../hooks/useSystemCapabilities";
import { humanCapabilityName } from "../utils";

export function CapabilityStatusPanel() {
  const { capabilities, error, message, mutationError, mutationPending, recalculateTravel } = useSystemCapabilities();
  const ordered = capabilities ? Object.entries(capabilities.states) : [];
  const flags = capabilities?.flags;

  return (
    <Section title="Capability Status" actions={<SlidersHorizontal className="h-5 w-5 text-slate-500" />}>
      <CapabilityNotice tone="neutral">
        Features are labeled honestly based on configured services, available data, and manual workflow requirements.
      </CapabilityNotice>
      {flags && (
        <div className="mb-3 flex flex-wrap gap-2 text-xs">
          <StatusBadge>{flags.travel_provider_configured ? "Travel Configured" : "Travel Not Configured"}</StatusBadge>
          <StatusBadge>{flags.ai_configured ? "AI Configured" : "Deterministic Recommendation"}</StatusBadge>
          <StatusBadge>{flags.notifications_configured ? "Notifications Configured" : "Dashboard Alerts Only"}</StatusBadge>
          <StatusBadge>{flags.source_discovery_configured ? "Discovery Sources Active" : "Source Discovery Not Configured"}</StatusBadge>
          <StatusBadge>{flags.public_profile_import_configured ? "Profile Import Available" : "Profile Import Not Configured"}</StatusBadge>
        </div>
      )}
      {message && <p className="mb-3 rounded-md border border-green-200 bg-green-50 p-2 text-sm text-green-800">{message}</p>}
      <div className="mb-3">
        <Button variant="secondary" disabled={mutationPending} onClick={() => void recalculateTravel().catch(() => undefined)}>Recalculate Travel Exceptions</Button>
      </div>
      {error && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">Could not load capability status.</p>}
      {mutationError && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">Could not recalculate travel exceptions.</p>}
      {!capabilities ? (
        <EmptyState>Loading capability status...</EmptyState>
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {ordered.map(([key, value]) => (
            <article key={key} className="rounded-md border border-slate-200 p-3 text-xs">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold text-ink">{humanCapabilityName(key)}</h3>
                <StatusBadge>{value.state}</StatusBadge>
              </div>
              <p className="mt-2 text-slate-600">{value.explanation}</p>
              <p className="mt-2 font-medium text-slate-700">Fallback: {value.safe_fallback}</p>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}
