import { useSystemCapabilities } from "../../../services/system";
import { CapabilityStatusPanel } from "./CapabilityStatusPanel";
import { DiscoveryProviderSettingsPanel } from "./DiscoveryProviderSettingsPanel";
import { IntegrationsStatusPanel } from "./IntegrationsStatusPanel";
import { PrivacyDataControlsPanel } from "./PrivacyDataControlsPanel";

export function SettingsPanel() {
  const capabilities = useSystemCapabilities();
  return (
    <div className="grid gap-4">
      {capabilities.isError && <p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">System capabilities could not load. Provider configuration remains available.</p>}
      <IntegrationsStatusPanel capabilities={capabilities.data ?? null} />
      <CapabilityStatusPanel />
      <DiscoveryProviderSettingsPanel />
      <PrivacyDataControlsPanel />
    </div>
  );
}
