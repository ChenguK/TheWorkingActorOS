from __future__ import annotations

from dataclasses import dataclass

from app.automation.discovery.contracts import (
    DiscoveryProvider,
    DiscoveryProviderHealth,
    NormalizedOpportunity,
)
from app.automation.discovery.public_sources import PublicPlaybillJobsSource


@dataclass(frozen=True)
class ProviderDefinition:
    name: str
    implementation_key: str
    tier: int
    category: str
    source_type: str
    priority_rank: int
    reliability_score: float
    authentication_methods: tuple[str, ...]
    default_enabled: bool = False
    default_poll_frequency_minutes: int = 1440
    notes: str | None = None


class PlaceholderDiscoveryProvider(DiscoveryProvider):
    provider_kind = "placeholder"

    def __init__(self, definition: ProviderDefinition) -> None:
        self.definition = definition
        self.name = definition.name
        self.implementation_key = definition.implementation_key
        self.tier = definition.tier
        self.category = definition.category
        self.source_type = definition.source_type
        self.priority_rank = definition.priority_rank
        self.reliability_score = definition.reliability_score
        self.authentication_methods = definition.authentication_methods
        self.default_poll_frequency_minutes = definition.default_poll_frequency_minutes
        self.notes = definition.notes

    def discover(self) -> list[dict]:
        return []

    def normalize(self, raw_items: list[dict]) -> list[NormalizedOpportunity]:
        return []

    def health_check(self) -> DiscoveryProviderHealth:
        return DiscoveryProviderHealth(
            status="configured",
            message=(
                "Provider registered. Discovery implementation is intentionally disabled until a safe, "
                "user-authorized integration is added."
            ),
            details={
                "category": self.category,
                "tier": self.tier,
                "authentication_methods": list(self.authentication_methods),
                "provider_kind": self.provider_kind,
            },
        )


class SupervisedPlatformProvider(PlaceholderDiscoveryProvider):
    provider_kind = "supervised_platform"

    def health_check(self) -> DiscoveryProviderHealth:
        return DiscoveryProviderHealth(
            status="manual_required",
            message=(
                "Professional platform discovery must be user-supervised. The app will not store passwords, "
                "bypass access controls, or crawl logged-in pages unattended."
            ),
            details={
                "allowed_methods": list(self.authentication_methods),
                "provider_kind": self.provider_kind,
            },
        )


class SocialDiscoveryProvider(PlaceholderDiscoveryProvider):
    provider_kind = "social_discovery"

    def health_check(self) -> DiscoveryProviderHealth:
        return DiscoveryProviderHealth(
            status="manual_or_api_required",
            message=(
                "Social discovery is registered for future API/manual-review workflows. No background social "
                "scraping is performed."
            ),
            details={"provider_kind": self.provider_kind},
        )


class PublicCastingSiteProvider(PlaceholderDiscoveryProvider):
    provider_kind = "public_casting_site"


class CastingOfficeProvider(PlaceholderDiscoveryProvider):
    provider_kind = "casting_office"


class FilmCommissionProvider(PlaceholderDiscoveryProvider):
    provider_kind = "film_commission"


PROVIDER_DEFINITIONS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        "Actors Access",
        "actors_access",
        1,
        "Professional Platforms",
        "platform",
        10,
        0.95,
        ("Supervised Browser", "Manual Copy/Paste", "PDF Upload", "Screenshot Upload"),
        notes="Protected professional platform. Use supervised, user-triggered import only.",
    ),
    ProviderDefinition(
        "Casting Networks",
        "casting_networks",
        1,
        "Professional Platforms",
        "platform",
        20,
        0.95,
        ("Supervised Browser", "Public/Shareable URL", "Manual Copy/Paste", "PDF Upload"),
        notes="Protected professional platform. Public/shareable profile data may be imported when user-provided.",
    ),
    ProviderDefinition(
        "Casting Frontier",
        "casting_frontier",
        1,
        "Professional Platforms",
        "platform",
        30,
        0.93,
        ("Supervised Browser", "Manual Copy/Paste", "PDF Upload", "Screenshot Upload"),
        notes="Protected professional platform. Use supervised, user-triggered import only.",
    ),
    ProviderDefinition("Backstage", "backstage", 2, "Public Casting Sites", "public_breakdowns", 110, 0.82, ("None", "Public URL")),
    ProviderDefinition("Mandy", "mandy", 2, "Public Casting Sites", "public_breakdowns", 120, 0.78, ("None", "Public URL")),
    ProviderDefinition(
        "Project Casting",
        "project_casting",
        2,
        "Public Casting Sites",
        "public_breakdowns",
        130,
        0.72,
        ("None", "Public URL"),
    ),
    ProviderDefinition("NYCastings", "nycastings", 2, "Public Casting Sites", "public_breakdowns", 140, 0.76, ("None", "Public URL")),
    ProviderDefinition(
        "Telsey Office",
        "telsey_office",
        3,
        "Casting Offices",
        "casting_office",
        210,
        0.86,
        ("Public Website", "Manual Entry", "Email Import"),
    ),
    ProviderDefinition(
        "Waldron Casting",
        "waldron_casting",
        3,
        "Casting Offices",
        "casting_office",
        220,
        0.82,
        ("Public Website", "Manual Entry", "Email Import"),
    ),
    ProviderDefinition(
        "Grant Wilfley Casting",
        "grant_wilfley_casting",
        3,
        "Casting Offices",
        "casting_office",
        230,
        0.84,
        ("Public Website", "Manual Entry", "Email Import"),
    ),
    ProviderDefinition("Instagram", "instagram", 4, "Social Discovery", "social", 310, 0.62, ("Manual URL", "Official API")),
    ProviderDefinition("Facebook", "facebook", 4, "Social Discovery", "social", 320, 0.6, ("Manual URL", "Official API")),
    ProviderDefinition("Threads", "threads", 4, "Social Discovery", "social", 330, 0.58, ("Manual URL", "Official API")),
    ProviderDefinition("LinkedIn", "linkedin", 4, "Social Discovery", "social", 340, 0.72, ("Manual URL", "Official API")),
    ProviderDefinition(
        "New York Film Commission",
        "new_york_film_commission",
        5,
        "Film Commission Discovery",
        "film_commission",
        410,
        0.7,
        ("Public Website", "Manual Entry"),
    ),
    ProviderDefinition(
        "Georgia Film Commission",
        "georgia_film_commission",
        5,
        "Film Commission Discovery",
        "film_commission",
        420,
        0.7,
        ("Public Website", "Manual Entry"),
    ),
    ProviderDefinition(
        "New Jersey Film Commission",
        "new_jersey_film_commission",
        5,
        "Film Commission Discovery",
        "film_commission",
        430,
        0.7,
        ("Public Website", "Manual Entry"),
    ),
    ProviderDefinition(
        "Pennsylvania Film Commission",
        "pennsylvania_film_commission",
        5,
        "Film Commission Discovery",
        "film_commission",
        440,
        0.7,
        ("Public Website", "Manual Entry"),
    ),
    ProviderDefinition(
        "UK Film Commission",
        "uk_film_commission",
        5,
        "Film Commission Discovery",
        "film_commission",
        450,
        0.7,
        ("Public Website", "Manual Entry"),
    ),
)


def build_discovery_providers() -> list[DiscoveryProvider]:
    providers: list[DiscoveryProvider] = [PublicPlaybillJobsSource()]
    for definition in PROVIDER_DEFINITIONS:
        if definition.tier == 1:
            providers.append(SupervisedPlatformProvider(definition))
        elif definition.tier == 2:
            providers.append(PublicCastingSiteProvider(definition))
        elif definition.tier == 3:
            providers.append(CastingOfficeProvider(definition))
        elif definition.tier == 4:
            providers.append(SocialDiscoveryProvider(definition))
        elif definition.tier == 5:
            providers.append(FilmCommissionProvider(definition))
        else:
            providers.append(PlaceholderDiscoveryProvider(definition))
    return providers
