import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import { systemCapabilitiesKey } from "../../../services/system";
import { healthCheckDiscoveryProvider, listDiscoveryProviders, updateDiscoveryProvider } from "../api";
import type { DiscoveryProviderSettings } from "../types";

export const settingsKeys = {
  discoveryProviders: queryKeys.settings.list({ resource: "discoveryProviders" })
} as const;

export function useDiscoveryProviders() {
  const client = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const providersQuery = useQuery({
    queryKey: settingsKeys.discoveryProviders,
    queryFn: listDiscoveryProviders,
    staleTime: queryStaleTimes.configuration,
    refetchOnMount: false
  });
  const updateMutation = useMutation({
    mutationFn: ({ providerKey, patch }: { providerKey: string; patch: Partial<DiscoveryProviderSettings> }) => updateDiscoveryProvider(providerKey, patch),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: settingsKeys.discoveryProviders }),
        client.invalidateQueries({ queryKey: systemCapabilitiesKey })
      ]);
    }
  });
  const healthMutation = useMutation({
    mutationFn: (providerKey: string) => healthCheckDiscoveryProvider(providerKey),
    onSuccess: async (saved) => {
      setMessage(`${saved.display_name}: ${saved.health_status}`);
      await client.invalidateQueries({ queryKey: settingsKeys.discoveryProviders });
    }
  });
  const providers = useMemo(() => providersQuery.data ?? [], [providersQuery.data]);
  const grouped = useMemo(() => providers.reduce<Record<string, DiscoveryProviderSettings[]>>((groups, provider) => {
    const label = `Tier ${provider.tier}: ${provider.category}`;
    groups[label] = [...(groups[label] ?? []), provider];
    return groups;
  }, {}), [providers]);

  return {
    grouped,
    message,
    providers,
    loading: providersQuery.isLoading,
    error: providersQuery.error,
    mutationError: updateMutation.error ?? healthMutation.error,
    mutationPending: updateMutation.isPending || healthMutation.isPending,
    updateProvider: (provider: DiscoveryProviderSettings, patch: Partial<DiscoveryProviderSettings>) => updateMutation.mutateAsync({ providerKey: provider.provider_key, patch }),
    healthCheck: (provider: DiscoveryProviderSettings) => healthMutation.mutateAsync(provider.provider_key)
  };
}
