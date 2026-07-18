from __future__ import annotations

from app.automation.discovery.contracts import DiscoveryProvider
from app.automation.discovery.providers import build_discovery_providers


class DiscoveryPluginRegistry:
    def __init__(self) -> None:
        self._plugins = {provider.implementation_key: provider for provider in build_discovery_providers()}

    def list(self) -> list[DiscoveryProvider]:
        return sorted(self._plugins.values(), key=lambda plugin: plugin.priority_rank)

    def get(self, key: str) -> DiscoveryProvider:
        return self._plugins[key]
