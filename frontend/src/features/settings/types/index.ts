import type {
  DiscoveryProviderSettings,
  SystemCapabilities
} from "../../../types/domain";

export type {
  DiscoveryProviderSettings,
  SystemCapabilities
};

export type IntegrationStatus = SystemCapabilities["integrations"][number];
export type IntegrationKey = IntegrationStatus["id"];
export type ProviderConfiguration = DiscoveryProviderSettings;
export type SystemPreference = {
  key: string;
  value: unknown;
};
export type ConfigurationInstruction = {
  integrationId: IntegrationKey;
  setupInstructions: string;
  fallbackBehavior: string;
};
