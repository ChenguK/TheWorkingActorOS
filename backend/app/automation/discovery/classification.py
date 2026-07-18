from __future__ import annotations

from dataclasses import dataclass


ACTOR_FACING_CLASSIFICATIONS = {
    "Acting Role",
    "Background Role",
    "Voiceover Role",
    "Theater Role",
    "Commercial Role",
}

REJECTED_CLASSIFICATIONS = {"Non-Acting Job", "Crew Job"}

ACTING_ROLE_SIGNALS = (
    "role:",
    "role name",
    "character description",
    "audition",
    "self-tape",
    "self tape",
    "casting call",
    "seeking actors",
    "seeking actor",
    "seeking performers",
    "performers",
    "performer",
    "talent",
    "sides",
    "callback",
    "callbacks",
    "shoot dates",
    "shoot date",
    "role type",
    "union status",
    "submission instructions",
    "submit headshot",
    "submit resume",
)

NON_ACTING_JOB_SIGNALS = (
    "casting coordinator",
    "casting assistant",
    "casting director job",
    "casting associate",
    "theater administrator",
    "theatre administrator",
    "admin assistant",
    "administrative assistant",
    "full-time",
    "part-time",
    "salary",
    "hourly",
    "benefits",
    "apply for this job",
    "employment",
    "staff position",
    "job opening",
    "career opportunity",
    "teaching artist",
    "instructor",
    "workshop",
    "class registration",
    "internship",
    "intern ",
)

CREW_JOB_SIGNALS = (
    "production assistant",
    "crew",
    "gaffer",
    "grip",
    "editor",
    "camera operator",
    "sound mixer",
    "wardrobe supervisor",
    "stage manager",
    "props",
    "lighting designer",
)


@dataclass(frozen=True)
class BreakdownClassification:
    classification: str
    rejection_reason: str | None = None


def classify_breakdown_text(text: str) -> BreakdownClassification:
    normalized = " ".join(text.lower().split())
    has_acting_signal = any(signal in normalized for signal in ACTING_ROLE_SIGNALS)

    if any(signal in normalized for signal in CREW_JOB_SIGNALS) and not has_acting_signal:
        return BreakdownClassification(
            "Crew Job",
            "This is a crew or production job listing, not an acting breakdown.",
        )

    if any(signal in normalized for signal in NON_ACTING_JOB_SIGNALS) and not has_acting_signal:
        return BreakdownClassification(
            "Non-Acting Job",
            "This is an employment/job listing, not an acting breakdown.",
        )

    if not has_acting_signal:
        return BreakdownClassification("Unknown")

    if "voiceover" in normalized or "voice over" in normalized or " vo " in f" {normalized} ":
        return BreakdownClassification("Voiceover Role")
    if "background" in normalized or "extra" in normalized or "extras" in normalized:
        return BreakdownClassification("Background Role")
    if "commercial" in normalized:
        return BreakdownClassification("Commercial Role")
    if any(signal in normalized for signal in ("theater", "theatre", "epa", "ecc", "musical", "play ")):
        return BreakdownClassification("Theater Role")
    return BreakdownClassification("Acting Role")


def is_actor_facing_classification(classification: str) -> bool:
    return classification in ACTOR_FACING_CLASSIFICATIONS
