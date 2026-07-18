import { SlidersHorizontal } from "lucide-react";
import { CapabilityNotice, EmptyState, Section, StatusBadge } from "../../../components/ui";
import type { SystemCapabilities } from "../types";

export function IntegrationsStatusPanel({ capabilities }: { capabilities: SystemCapabilities | null }) {
  return (
    <Section title="Integrations & API Status" actions={<SlidersHorizontal className="h-5 w-5 text-slate-500" />}>
      <CapabilityNotice tone="neutral">
        API keys are read from backend environment variables only. This page shows configuration status without exposing secrets to the browser.
      </CapabilityNotice>
      {!capabilities ? (
        <EmptyState>Loading integration status...</EmptyState>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {capabilities.integrations.map((integration) => (
            <article key={integration.id} className="rounded-md border border-slate-200 bg-white p-3 text-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-ink">{integration.name}</h3>
                  {integration.provider && <p className="mt-1 text-xs text-slate-500">Provider: {integration.provider}</p>}
                </div>
                <StatusBadge>{integration.status}</StatusBadge>
              </div>
              <dl className="mt-3 grid gap-2 text-xs text-slate-700">
                <div>
                  <dt className="font-semibold text-ink">Configured</dt>
                  <dd>{integration.configured ? "Configured" : "Not configured"}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-ink">Enables</dt>
                  <dd>{integration.what_it_enables}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-ink">Fallback</dt>
                  <dd>{integration.fallback_behavior}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-ink">Setup</dt>
                  <dd>{integration.setup_instructions}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      )}
    </Section>
  );
}
