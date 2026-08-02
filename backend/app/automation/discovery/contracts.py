from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NormalizedOpportunity:
    role: str
    project: str
    union: str
    location: str
    description: str
    original_post_url: str | None
    audition_type: str
    audition_travel_hours: float | None
    travel_covered: bool | None = None
    housing_covered: bool | None = None
    source_name: str = "Mock Source"
    category: str = "General Casting"
    source_reliability_score: float = 0.7
    breakdown_classification: str = "Unknown"
    rejection_reason: str | None = None
    source_metadata: dict = field(default_factory=dict)
    production_details: dict = field(default_factory=dict)
    role_details: dict = field(default_factory=dict)
    ai_summary: str | None = None
    is_demo_data: bool = False
    result_type: str = "breakdown"


@dataclass(frozen=True)
class DiscoveryProviderHealth:
    status: str
    message: str
    checked_at: str | None = None
    details: dict | None = None


class DiscoveryProvider:
    name: str
    priority_rank: int
    source_type: str
    implementation_key: str
    reliability_score: float
    category: str = "Public Casting Sites"
    tier: int = 2
    provider_kind: str = "placeholder"
    authentication_methods: tuple[str, ...] = ("None",)
    default_poll_frequency_minutes: int = 1440
    notes: str | None = None
    operational_adapter: bool = False

    def discover(self) -> list[dict]:
        raise NotImplementedError

    def normalize(self, raw_items: list[dict]) -> list[NormalizedOpportunity]:
        raise NotImplementedError

    def validate(self, opportunity: NormalizedOpportunity) -> bool:
        return bool(
            opportunity.result_type == "breakdown"
            and opportunity.original_post_url
            and opportunity.role
            and opportunity.project
            and opportunity.union
            and opportunity.location
            and opportunity.description
        )

    def deduplicate(self, opportunities: list[NormalizedOpportunity]) -> list[NormalizedOpportunity]:
        seen: set[str] = set()
        unique: list[NormalizedOpportunity] = []
        for opportunity in opportunities:
            key = f"{opportunity.project}|{opportunity.role}|{opportunity.location}".lower()
            if key not in seen:
                seen.add(key)
                unique.append(opportunity)
        return unique

    def health_check(self) -> DiscoveryProviderHealth:
        return DiscoveryProviderHealth(
            status="available",
            message="Provider interface is available.",
            details={"provider_kind": self.provider_kind},
        )


DiscoverySourcePlugin = DiscoveryProvider
