from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.db.models import ActorProfile, Opportunity


COMPATIBILITY_LABELS = (
    "Excellent Match",
    "Strong Match",
    "Good Match",
    "Comfortable Stretch",
    "Stretch",
    "Low Fit",
    "Not Recommended",
)

AGE_LABELS = ("Direct Match", "Comfortable Stretch", "Significant Stretch", "Unlikely")


@dataclass(frozen=True)
class CompatibilityDecision:
    label: str
    hard_status: str
    score: int
    explanation: str
    details: dict[str, Any]


class CompatibilityEngine:
    """Evaluate casting fit using casting-style labels and explainable categories."""

    def age_compatibility(
        self,
        actor_ranges: list[tuple[int, int]],
        role_ranges: list[tuple[int, int]],
    ) -> CompatibilityDecision:
        if not role_ranges:
            return CompatibilityDecision(
                label="Good Match",
                hard_status="Not Specified",
                score=60,
                explanation="The breakdown does not list a specific playable age range.",
                details={"age_compatibility": "Not Specified"},
            )
        if not actor_ranges:
            return CompatibilityDecision(
                label="Low Fit",
                hard_status="Needs Review",
                score=35,
                explanation="The role lists an age range, but the actor profile has no playable age range to compare.",
                details={"age_compatibility": "Needs Review"},
            )

        best = self._best_age_pair(actor_ranges, role_ranges)
        actor_range = best["actor_range"]
        role_range = best["role_range"]
        role_width = max(1, role_range[1] - role_range[0] + 1)
        overlap_width = max(0, min(actor_range[1], role_range[1]) - max(actor_range[0], role_range[0]) + 1)
        overlap_ratio = overlap_width / role_width
        gap = self._range_gap(actor_range, role_range)

        if actor_range[0] <= role_range[0] and actor_range[1] >= role_range[1]:
            age_label = "Direct Match"
            hard_status = "Match"
            score = 95
            explanation = (
                f"Role age {role_range[0]}-{role_range[1]} sits inside the actor's marketed playable age "
                f"{actor_range[0]}-{actor_range[1]}."
            )
        elif overlap_width >= 3 and overlap_ratio >= 0.4:
            age_label = "Comfortable Stretch"
            hard_status = "Match"
            score = 78
            explanation = (
                f"Role age {role_range[0]}-{role_range[1]} overlaps the actor's marketed range "
                f"{actor_range[0]}-{actor_range[1]}, but it is not a perfect age-box match."
            )
        elif overlap_width > 0 or gap <= 2:
            age_label = "Comfortable Stretch"
            hard_status = "Match"
            score = 72
            explanation = (
                f"Actor currently markets up to age {actor_range[1]}. Role begins at {role_range[0]}; "
                "this is a plausible edge-of-range stretch, not a perfect match."
            )
        elif gap <= 7:
            age_label = "Significant Stretch"
            hard_status = "Needs Review"
            score = 45
            explanation = (
                f"Role age {role_range[0]}-{role_range[1]} is outside the actor's marketed range "
                f"{actor_range[0]}-{actor_range[1]}, but close enough to review manually."
            )
        else:
            age_label = "Unlikely"
            hard_status = "Not a Match"
            score = 10
            explanation = (
                f"Role age {role_range[0]}-{role_range[1]} is too far from the actor's marketed playable age "
                f"{actor_range[0]}-{actor_range[1]}."
            )

        return CompatibilityDecision(
            label=age_label,
            hard_status=hard_status,
            score=score,
            explanation=explanation,
            details={
                "age_compatibility": age_label,
                "actor_range": f"{actor_range[0]}-{actor_range[1]}",
                "role_range": f"{role_range[0]}-{role_range[1]}",
                "overlap_years": overlap_width,
                "gap_years": gap,
            },
        )

    def role_compatibility(
        self,
        *,
        actor: ActorProfile,
        opportunity: Opportunity,
        role_name: str,
        demographic_checks: list[dict[str, Any]],
    ) -> CompatibilityDecision:
        hard_mismatches = [check for check in demographic_checks if check.get("status") == "Not a Match"]
        reviews = [check for check in demographic_checks if check.get("status") == "Needs Review"]
        matches = [check for check in demographic_checks if check.get("status") == "Match"]
        age_check = next((check for check in demographic_checks if check.get("label") == "Playable Age"), None)
        age_label = (age_check or {}).get("compatibility_label")

        if hard_mismatches:
            label = "Not Recommended"
            hard_status = "Not a Match"
            score = 10
        elif age_label == "Significant Stretch" or reviews:
            label = "Stretch"
            hard_status = "Needs Review"
            score = 45
        elif age_label == "Comfortable Stretch":
            label = "Comfortable Stretch"
            hard_status = "Match"
            score = 72
        elif len(matches) >= 3:
            label = "Strong Match"
            hard_status = "Match"
            score = 82
        elif matches:
            label = "Good Match"
            hard_status = "Match"
            score = 70
        else:
            label = "Good Match"
            hard_status = "Match"
            score = 60

        category_notes = self._category_notes(actor, opportunity, demographic_checks)
        explanation = (
            f"{role_name} is a {label.lower()} because {self._plain_check_summary(demographic_checks)} "
            f"{' '.join(category_notes)}"
        ).strip()
        return CompatibilityDecision(
            label=label,
            hard_status=hard_status,
            score=score,
            explanation=explanation,
            details={
                "label": label,
                "score": score,
                "demographics": self._check_details(demographic_checks),
                "character": "Character interpretation is considered when role archetypes are available.",
                "career_goals": "Casting goals and watch lists may raise priority when aligned.",
                "materials": "Material fit is evaluated by the Strategy Agent against saved headshots, reels, slates, and resumes.",
                "travel": self._travel_note(opportunity),
                "availability": self._availability_note(opportunity),
                "learning_history": "Outcome history is used when similar roles and materials have prior callbacks or bookings.",
            },
        )

    def _best_age_pair(
        self,
        actor_ranges: list[tuple[int, int]],
        role_ranges: list[tuple[int, int]],
    ) -> dict[str, tuple[int, int]]:
        def closeness(actor_range: tuple[int, int], role_range: tuple[int, int]) -> tuple[int, int]:
            overlap = max(0, min(actor_range[1], role_range[1]) - max(actor_range[0], role_range[0]) + 1)
            gap = self._range_gap(actor_range, role_range)
            return (-overlap, gap)

        actor_range, role_range = min(
            ((actor_range, role_range) for actor_range in actor_ranges for role_range in role_ranges),
            key=lambda pair: closeness(pair[0], pair[1]),
        )
        return {"actor_range": actor_range, "role_range": role_range}

    def _range_gap(self, first: tuple[int, int], second: tuple[int, int]) -> int:
        if first[0] <= second[1] and second[0] <= first[1]:
            return 0
        if first[1] < second[0]:
            return second[0] - first[1]
        return first[0] - second[1]

    def _plain_check_summary(self, checks: list[dict[str, Any]]) -> str:
        summaries = []
        for check in checks:
            if check.get("status") == "Not Specified":
                continue
            label = check.get("label", "Requirement")
            compatibility = check.get("compatibility_label") or check.get("status")
            summaries.append(f"{label}: {compatibility}")
        return "; ".join(summaries) + "." if summaries else "the breakdown has limited explicit demographic requirements."

    def _check_details(self, checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "label": check.get("label"),
                "decision": check.get("compatibility_label") or check.get("status"),
                "status": check.get("status"),
                "explanation": check.get("explanation"),
            }
            for check in checks
            if check.get("status") != "Not Specified"
        ]

    def _category_notes(self, actor: ActorProfile, opportunity: Opportunity, checks: list[dict[str, Any]]) -> list[str]:
        notes = []
        if opportunity.project_type:
            notes.append(f"Project type: {opportunity.project_type}.")
        if opportunity.audition_type:
            notes.append(f"Audition type: {opportunity.audition_type}.")
        if actor.skills:
            notes.append("Saved skills can strengthen fit when they appear in the role requirements.")
        return notes

    def _travel_note(self, opportunity: Opportunity) -> str:
        if opportunity.audition_type in {"Self-Tape", "Virtual"}:
            return f"{opportunity.audition_type} auditions do not trigger the in-person audition travel limit."
        if opportunity.audition_travel_hours is not None:
            return f"Audition travel is approximately {opportunity.audition_travel_hours} hours."
        return "Audition travel is not fully known yet."

    def _availability_note(self, opportunity: Opportunity) -> str:
        dates = [opportunity.submission_deadline, opportunity.audition_deadline, opportunity.callback_date]
        if any(dates):
            return "Known audition or submission dates can be checked against saved availability."
        return "No dated availability conflict can be checked yet."
