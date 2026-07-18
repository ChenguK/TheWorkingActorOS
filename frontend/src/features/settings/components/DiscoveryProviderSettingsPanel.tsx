import { SlidersHorizontal } from "lucide-react";
import { Badge, Button, EmptyState, Field, Section, inputClass } from "../../../components/ui";
import { useDiscoveryProviders } from "../hooks/useDiscoveryProviders";

export function DiscoveryProviderSettingsPanel() {
  const { grouped, healthCheck, loading, error, message, mutationError, mutationPending, providers, updateProvider } = useDiscoveryProviders();

  return (
    <Section title="Breakdown Source Providers" actions={<SlidersHorizontal className="h-5 w-5 text-slate-500" />}>
      <p className="mb-3 text-sm text-slate-600">
        Enable only the sources you want the app to check. Professional platforms stay supervised and user-triggered; protected pages are not scraped unattended.
      </p>
      {message && <p className="mb-3 rounded bg-slate-50 p-2 text-sm text-slate-700">{message}</p>}
      {error && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">Could not load discovery providers.</p>}
      {mutationError && <p role="alert" className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">Could not update this discovery provider.</p>}
      {loading ? (
        <EmptyState>Loading breakdown source providers...</EmptyState>
      ) : providers.length === 0 ? (
        <EmptyState>No breakdown source providers configured yet.</EmptyState>
      ) : (
        <div className="grid gap-4">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="grid gap-3">
              <h3 className="text-sm font-semibold text-slate-800">{group}</h3>
              <div className="grid gap-3 lg:grid-cols-2">
                {items.map((provider) => (
                  <article key={provider.provider_key} className="rounded-md border border-slate-200 p-3 text-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="font-semibold">{provider.display_name}</h4>
                        <p className="text-slate-600">{provider.source_type} · priority {provider.priority}</p>
                      </div>
                      <Badge>{provider.enabled ? "Enabled" : "Disabled"}</Badge>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <label className="flex items-center gap-2 text-sm text-slate-700">
                        <input
                          name={`provider_enabled_${provider.provider_key}`}
                          type="checkbox"
                          checked={provider.enabled}
                          disabled={mutationPending}
                          onChange={(event) => void updateProvider(provider, { enabled: event.target.checked }).catch(() => undefined)}
                        />
                        Enabled
                      </label>
                      <Field label="Auth Method">
                        <select
                          className={inputClass}
                          value={provider.authentication_method}
                          disabled={mutationPending}
                          onChange={(event) => void updateProvider(provider, { authentication_method: event.target.value }).catch(() => undefined)}
                        >
                          {provider.supported_authentication_methods.map((method) => (
                            <option key={method}>{method}</option>
                          ))}
                        </select>
                      </Field>
                      <Field label="Poll Frequency Minutes">
                        <input
                          className={inputClass}
                          type="number"
                          min={0}
                          value={provider.poll_frequency_minutes}
                          disabled={mutationPending}
                          onChange={(event) => void updateProvider(provider, { poll_frequency_minutes: Number(event.target.value) }).catch(() => undefined)}
                        />
                      </Field>
                      <Field label="Priority">
                        <input
                          className={inputClass}
                          type="number"
                          min={0}
                          value={provider.priority}
                          disabled={mutationPending}
                          onChange={(event) => void updateProvider(provider, { priority: Number(event.target.value) }).catch(() => undefined)}
                        />
                      </Field>
                    </div>
                    <div className="mt-3">
                      <Field label="Notes">
                        <textarea
                          className={inputClass}
                          value={provider.notes ?? ""}
                          disabled={mutationPending}
                          onChange={(event) => void updateProvider(provider, { notes: event.target.value || null }).catch(() => undefined)}
                        />
                      </Field>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button variant="secondary" disabled={mutationPending} onClick={() => void healthCheck(provider).catch(() => undefined)}>Health Check</Button>
                      <span className="text-xs text-slate-500">
                        Health: {provider.health_status}
                        {provider.last_health_check_at ? ` · ${new Date(provider.last_health_check_at).toLocaleString()}` : ""}
                      </span>
                    </div>
                    {provider.health_message && <p className="mt-2 rounded bg-slate-50 p-2 text-xs text-slate-600">{provider.health_message}</p>}
                  </article>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}
