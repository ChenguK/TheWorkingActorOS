import { api } from "../../../services/api";
import type { DiscoveryProviderSettings } from "../../../types/domain";

export function recalculateTravelExceptions() {
  return api.post<Record<string, number>>("/automation/travel/recalculate");
}

export function listDiscoveryProviders() {
  return api.get<DiscoveryProviderSettings[]>("/automation/discovery/providers");
}

export function updateDiscoveryProvider(providerKey: string, patch: Partial<DiscoveryProviderSettings>) {
  return api.patch<DiscoveryProviderSettings>(`/automation/discovery/providers/${providerKey}`, patch);
}

export function healthCheckDiscoveryProvider(providerKey: string) {
  return api.post<DiscoveryProviderSettings>(`/automation/discovery/providers/${providerKey}/health-check`);
}
