from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, Opportunity
from app.services.compatibility_engine import CompatibilityEngine


@dataclass(frozen=True)
class TermGroup:
    label: str
    terms: tuple[str, ...]


GENDER_GROUPS = (
    TermGroup("Woman / Female", ("woman", "women", "female", "girl", "girls", "she/her", "femme", "feminine")),
    TermGroup("Man / Male", ("man", "men", "male", "boy", "boys", "he/him", "masc", "masculine")),
    TermGroup(
        "Nonbinary",
        ("nonbinary", "non-binary", "gender nonconforming", "gender-nonconforming", "genderqueer", "they/them"),
    ),
    TermGroup("Trans", ("trans", "transgender", "trans woman", "trans man")),
)

IDENTITY_GROUPS = (
    TermGroup(
        "Black / African American",
        (
            "black",
            "african american",
            "african-american",
            "african descent",
            "african-descent",
            "afro",
            "afro-latine",
            "afro latine",
            "jamaican",
            "haitian",
            "nigerian",
            "ghanaian",
            "ethiopian",
            "somali",
            "sierra leonean",
            "liberian",
            "kenyan",
            "barbadian",
            "bahamian",
        ),
    ),
    TermGroup("African", ("african", "west african", "east african", "south african", "north african")),
    TermGroup("Caribbean", ("caribbean", "west indian", "jamaican", "haitian", "trinidadian", "barbadian", "bahamian")),
    TermGroup(
        "Latine / Hispanic",
        (
            "latine",
            "latina",
            "latino",
            "latinx",
            "hispanic",
            "mexican",
            "puerto rican",
            "cuban",
            "dominican",
            "brazilian",
            "central american",
            "south american",
            "spanish",
        ),
    ),
    TermGroup("Asian", ("asian", "asian american")),
    TermGroup("East Asian", ("east asian", "chinese", "japanese", "korean", "taiwanese")),
    TermGroup("South Asian", ("south asian", "indian", "pakistani", "bangladeshi", "sri lankan", "nepali")),
    TermGroup("Southeast Asian", ("southeast asian", "filipino", "vietnamese", "thai", "cambodian", "laotian", "hmong")),
    TermGroup(
        "Middle Eastern / North African",
        ("middle eastern", "mena", "north african", "arab", "persian", "iranian", "egyptian", "lebanese", "moroccan"),
    ),
    TermGroup(
        "Indigenous / Native American",
        ("indigenous", "native american", "american indian", "alaska native", "first nations", "maya", "aztec"),
    ),
    TermGroup("Native Hawaiian / Pacific Islander", ("native hawaiian", "pacific islander", "samoan", "chamorro", "tongan", "fijian")),
    TermGroup("White / Caucasian", ("white", "caucasian", "european", "italian", "irish", "german", "french", "british")),
    TermGroup("Biracial / Multiracial", ("biracial", "bi-racial", "multi-racial", "multiracial", "mixed race", "two or more races")),
)

DISABILITY_GROUPS = (
    TermGroup(
        "Disabled",
        (
            "disabled",
            "disability",
            "wheelchair",
            "mobility disability",
            "deaf",
            "hard of hearing",
            "blind",
            "low vision",
            "neurodivergent",
            "autistic",
            "adhd",
            "chronic illness",
        ),
    ),
)

LANGUAGE_GROUPS = (
    TermGroup("English", ("english",)),
    TermGroup("Spanish", ("spanish",)),
    TermGroup("French", ("french",)),
    TermGroup("Portuguese", ("portuguese",)),
    TermGroup("Arabic", ("arabic",)),
    TermGroup("Mandarin Chinese", ("mandarin", "mandarin chinese", "chinese")),
    TermGroup("Cantonese", ("cantonese",)),
    TermGroup("Japanese", ("japanese",)),
    TermGroup("Korean", ("korean",)),
    TermGroup("Vietnamese", ("vietnamese",)),
    TermGroup("Tagalog", ("tagalog", "filipino")),
    TermGroup("Hindi", ("hindi",)),
    TermGroup("Urdu", ("urdu",)),
    TermGroup("Bengali", ("bengali",)),
    TermGroup("Punjabi", ("punjabi",)),
    TermGroup("Russian", ("russian",)),
    TermGroup("German", ("german",)),
    TermGroup("Italian", ("italian",)),
    TermGroup("Greek", ("greek",)),
    TermGroup("Hebrew", ("hebrew",)),
    TermGroup("Yiddish", ("yiddish",)),
    TermGroup("American Sign Language", ("american sign language", "asl")),
    TermGroup("Haitian Creole", ("haitian creole", "creole")),
    TermGroup("Swahili", ("swahili",)),
    TermGroup("Yoruba", ("yoruba",)),
    TermGroup("Igbo", ("igbo",)),
    TermGroup("Twi", ("twi",)),
    TermGroup("Wolof", ("wolof",)),
    TermGroup("Krio", ("krio",)),
    TermGroup("Mende", ("mende",)),
    TermGroup("Temne", ("temne",)),
    TermGroup("Fula", ("fula", "fulani")),
)

ACCENT_GROUPS = (
    TermGroup("Standard American", ("standard american", "general american", "american accent")),
    TermGroup("New York", ("new york", "brooklyn", "bronx")),
    TermGroup("Boston", ("boston",)),
    TermGroup("Southern American", ("southern", "southern american")),
    TermGroup("British", ("british", "rp", "received pronunciation", "cockney")),
    TermGroup("Irish", ("irish",)),
    TermGroup("Scottish", ("scottish",)),
    TermGroup("French", ("french accent",)),
    TermGroup("Spanish", ("spanish accent",)),
    TermGroup("Italian", ("italian accent",)),
    TermGroup("German", ("german accent",)),
    TermGroup("Russian", ("russian accent",)),
    TermGroup("Middle Eastern", ("middle eastern accent", "arabic accent")),
    TermGroup("African", ("african accent", "west african", "east african")),
    TermGroup("Caribbean", ("caribbean accent", "jamaican", "haitian")),
    TermGroup("Nigerian", ("nigerian accent",)),
    TermGroup("Ghanaian", ("ghanaian accent",)),
    TermGroup("Sierra Leonean", ("sierra leonean accent", "krio accent")),
    TermGroup("South African", ("south african accent",)),
    TermGroup("Indian", ("indian accent",)),
    TermGroup("Chinese", ("chinese accent",)),
    TermGroup("Korean", ("korean accent",)),
    TermGroup("Japanese", ("japanese accent",)),
)


class DemographicMatchService:
    """Compare explicit breakdown requirements against actor-entered profile data."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def apply(self, opportunity: Opportunity, actor: ActorProfile | None = None) -> Opportunity:
        actor = actor or self.db.scalars(select(ActorProfile).limit(1)).first()
        if not actor:
            opportunity.demographic_match_status = "Needs Review"
            opportunity.demographic_match_explanation = (
                "Create an actor profile with playable age and demographics before checking breakdown fit."
            )
            opportunity.demographic_match_details = {}
            return opportunity

        text = self._opportunity_text(opportunity)
        available_roles = (opportunity.role_details or {}).get("available_roles")
        if isinstance(available_roles, list) and available_roles:
            return self._apply_role_specific(opportunity, actor, available_roles)

        checks = self._checks_for_text(text, actor)
        return self._apply_checks(opportunity, checks, actor)

    def _apply_role_specific(
        self,
        opportunity: Opportunity,
        actor: ActorProfile,
        available_roles: list[dict],
    ) -> Opportunity:
        role_results = []
        for role in available_roles:
            role_text = " ".join(
                str(value)
                for value in [
                    role.get("role_name"),
                    role.get("role_type"),
                    role.get("character_description"),
                    role.get("gender_presentation"),
                    role.get("ethnicity"),
                    role.get("age_range"),
                    role.get("height_requirement"),
                    role.get("role_requirement_text"),
                ]
                if value
            ).lower()
            checks = self._checks_for_text(role_text, actor, core_demographics_only=True)
            relevant_checks = [check for check in checks if check["status"] != "Not Specified"]
            hard_mismatches = [check for check in relevant_checks if check["status"] == "Not a Match"]
            review_checks = [check for check in relevant_checks if check["status"] == "Needs Review"]
            compatibility = CompatibilityEngine().role_compatibility(
                actor=actor,
                opportunity=opportunity,
                role_name=str(role.get("role_name", "Role")),
                demographic_checks=checks,
            )
            status = compatibility.hard_status
            role_results.append(
                {
                    "role_name": role.get("role_name", "Role"),
                    "status": status,
                    "compatibility_label": compatibility.label,
                    "compatibility_score": compatibility.score,
                    "compatibility_explanation": compatibility.explanation,
                    "compatibility_details": compatibility.details,
                    "checks": checks,
                    "detected_requirements": [
                        check for check in relevant_checks if check.get("detected_requirements")
                    ],
                }
            )

        if any(role["status"] == "Match" for role in role_results):
            status = "Match"
            best_label = self._best_compatibility_label(role_results)
            explanation = f"At least one role is currently a {best_label.lower()} based on saved profile compatibility."
        elif any(role["status"] == "Needs Review" for role in role_results):
            status = "Needs Review"
            explanation = (
                "No clear role match was found yet, but at least one role needs a human check because profile "
                "details are missing or the wording is ambiguous."
            )
        else:
            status = "Not a Match"
            explanation = (
                "The app parsed the individual roles in this breakdown and did not find a role whose explicit "
                "age, gender, ethnicity, or nationality requirements overlap your saved profile."
            )

        opportunity.demographic_match_status = status
        opportunity.demographic_match_explanation = explanation
        opportunity.demographic_match_details = {
            "role_results": role_results,
            "compatibility_labels": [
                role.get("compatibility_label") for role in role_results if role.get("compatibility_label")
            ],
            "profile_source": "Actor-entered profile data",
        }
        return opportunity

    def _checks_for_text(
        self,
        text: str,
        actor: ActorProfile,
        core_demographics_only: bool = False,
    ) -> list[dict]:
        checks = [
            self._age_check(text, actor),
            self._term_check(
                text=text,
                label="Gender",
                groups=GENDER_GROUPS,
                actor_values=[*actor.gender_identities, actor.gender_expression, actor.pronouns],
            ),
            self._term_check(
                text=text,
                label="Race / Ethnicity / Nationality",
                groups=IDENTITY_GROUPS,
                actor_values=[*actor.ethnicities, *actor.racial_identities, *actor.nationalities],
            ),
        ]
        if core_demographics_only:
            return checks
        checks.extend(
            [
            self._term_check(text=text, label="Language", groups=LANGUAGE_GROUPS, actor_values=actor.languages),
            self._term_check(text=text, label="Accent", groups=ACCENT_GROUPS, actor_values=actor.accents),
            self._term_check(
                text=text,
                label="Disability",
                groups=DISABILITY_GROUPS,
                actor_values=[*actor.disability_identities, actor.accessibility_notes],
                missing_is_review=True,
            ),
            ]
        )
        return checks

    def _apply_checks(self, opportunity: Opportunity, checks: list[dict], actor: ActorProfile | None = None) -> Opportunity:
        relevant_checks = [check for check in checks if check["status"] != "Not Specified"]
        hard_mismatches = [check for check in relevant_checks if check["status"] == "Not a Match"]
        review_checks = [check for check in relevant_checks if check["status"] == "Needs Review"]
        compatibility = (
            CompatibilityEngine().role_compatibility(
                actor=actor,
                opportunity=opportunity,
                role_name=opportunity.role,
                demographic_checks=checks,
            )
            if actor
            else None
        )

        if hard_mismatches:
            status = "Not a Match"
            explanation = (
                "This breakdown appears to include demographic requirements that do not overlap with the "
                "demographics saved in your profile. Review the role before spending time on it."
            )
        elif review_checks:
            status = "Needs Review"
            explanation = (
                "This breakdown includes demographic language, but your profile is missing matching details "
                "or the wording needs a human check."
            )
        else:
            status = "Match"
            explanation = (
                "No explicit demographic mismatch was detected against your saved profile. This is still a "
                "screening aid, not a casting decision."
            )

        opportunity.demographic_match_status = status
        opportunity.demographic_match_explanation = explanation
        opportunity.demographic_match_details = {
            "checks": checks,
            "detected_requirements": [
                check for check in relevant_checks if check.get("detected_requirements")
            ],
            "compatibility_label": compatibility.label if compatibility else None,
            "compatibility_score": compatibility.score if compatibility else None,
            "compatibility_explanation": compatibility.explanation if compatibility else None,
            "compatibility_details": compatibility.details if compatibility else {},
            "profile_source": "Actor-entered profile data",
        }
        return opportunity

    def refresh_all(self, actor: ActorProfile) -> None:
        for opportunity in self.db.scalars(select(Opportunity).where(Opportunity.is_demo_data.is_(False))).all():
            self.apply(opportunity, actor)

    def _opportunity_text(self, opportunity: Opportunity) -> str:
        return " ".join(
            item
            for item in [
                opportunity.role,
                opportunity.project,
                opportunity.project_type,
                opportunity.role_type,
                opportunity.description,
                " ".join(opportunity.archetypes or []),
            ]
            if item
        ).lower()

    def _age_check(self, text: str, actor: ActorProfile) -> dict:
        ranges = self._extract_age_ranges(text)
        if not ranges:
            return {
                "label": "Playable Age",
                "status": "Not Specified",
                "detected_requirements": [],
                "explanation": "No explicit age range was detected.",
            }
        actor_ranges = [(actor.playable_age_min, actor.playable_age_max)]
        if actor.secondary_playable_age_min is not None and actor.secondary_playable_age_max is not None:
            actor_ranges.append((actor.secondary_playable_age_min, actor.secondary_playable_age_max))
        decision = CompatibilityEngine().age_compatibility(actor_ranges, ranges)
        return {
            "label": "Playable Age",
            "status": decision.hard_status,
            "compatibility_label": decision.label,
            "compatibility_score": decision.score,
            "detected_requirements": [f"{start}-{end}" for start, end in ranges],
            "profile_values": [f"{start}-{end}" for start, end in actor_ranges],
            "explanation": decision.explanation,
            "compatibility_details": decision.details,
        }

    def _best_compatibility_label(self, role_results: list[dict]) -> str:
        order = {
            "Excellent Match": 7,
            "Strong Match": 6,
            "Good Match": 5,
            "Comfortable Stretch": 4,
            "Stretch": 3,
            "Low Fit": 2,
            "Not Recommended": 1,
        }
        labels = [str(role.get("compatibility_label")) for role in role_results if role.get("compatibility_label")]
        if not labels:
            return "match"
        return max(labels, key=lambda label: order.get(label, 0))

    def _term_check(
        self,
        text: str,
        label: str,
        groups: tuple[TermGroup, ...],
        actor_values: list[str | None],
        missing_is_review: bool = False,
    ) -> dict:
        open_terms = {
            "Gender": (
                "open gender",
                "all gender",
                "all genders",
                "any gender",
                "any gender identity",
                "all gender identities",
                "any gender presentation",
                "all gender presentations",
            ),
            "Race / Ethnicity / Nationality": (
                "open ethnicity",
                "any ethnicity",
                "any ethnic appearance",
                "all ethnicities",
                "all races",
                "any race",
                "any racial background",
                "all racial backgrounds",
                "open race",
                "open ethnicity/race",
                "all backgrounds",
            ),
        }.get(label, ())
        if open_terms and self._contains_any(text, open_terms):
            return {
                "label": label,
                "status": "Match",
                "detected_requirements": ["Open / Any"],
                "profile_values": [value for value in actor_values if value],
                "explanation": f"The breakdown lists {label.lower()} as open or any.",
            }
        detected = [group for group in groups if self._contains_any(text, group.terms)]
        if not detected:
            return {
                "label": label,
                "status": "Not Specified",
                "detected_requirements": [],
                "explanation": f"No explicit {label.lower()} requirement was detected.",
            }
        profile_text = " ".join(value or "" for value in actor_values).lower()
        if not profile_text.strip():
            return {
                "label": label,
                "status": "Needs Review" if missing_is_review or detected else "Not a Match",
                "detected_requirements": [group.label for group in detected],
                "profile_values": [],
                "explanation": f"The breakdown mentions {label.lower()}, but your profile has no saved values for this field.",
            }
        match = any(self._contains_any(profile_text, group.terms) for group in detected)
        return {
            "label": label,
            "status": "Match" if match else "Not a Match",
            "detected_requirements": [group.label for group in detected],
            "profile_values": [value for value in actor_values if value],
            "explanation": (
                f"Detected {label.lower()} language overlaps your saved profile."
                if match
                else f"Detected {label.lower()} language does not overlap your saved profile."
            ),
        }

    def _free_text_check(self, text: str, label: str, actor_values: list[str]) -> dict:
        actor_terms = [value.strip().lower() for value in actor_values if value.strip()]
        detected = [term for term in actor_terms if self._contains_phrase(text, term)]
        if detected:
            return {
                "label": label,
                "status": "Match",
                "detected_requirements": detected,
                "profile_values": actor_values,
                "explanation": f"Detected {label.lower()} language overlaps your saved profile.",
            }
        common_prefix = label.lower()
        if common_prefix in text and not actor_terms:
            return {
                "label": label,
                "status": "Needs Review",
                "detected_requirements": [f"{label} requirement mentioned"],
                "profile_values": [],
                "explanation": f"The breakdown mentions {label.lower()}, but your profile has no saved values for this field.",
            }
        return {
            "label": label,
            "status": "Not Specified",
            "detected_requirements": [],
            "explanation": f"No explicit {label.lower()} requirement was detected.",
        }

    def _extract_age_ranges(self, text: str) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        for match in re.finditer(r"\b(?:ages?|playing age|appears?)?\s*(\d{2})\s*(?:-|–|to)\s*(\d{2})\b", text):
            start, end = int(match.group(1)), int(match.group(2))
            if 13 <= start <= 100 and 13 <= end <= 100:
                ranges.append((min(start, end), max(start, end)))
        for match in re.finditer(r"\bshould\s+read\s+(?:age\s+)?(\d{2})\b", text):
            age = int(match.group(1))
            if 13 <= age <= 100:
                ranges.append((age, age))
        if re.search(r"\blate\s+teens\b", text):
            ranges.append((17, 19))
        if re.search(r"\bmid\s+teens\b", text):
            ranges.append((15, 17))
        if re.search(r"\bearly\s+teens\b", text):
            ranges.append((13, 15))
        for match in re.finditer(r"\b(?:late|early|mid)\s+(\d{2})s\b", text):
            decade = int(match.group(1))
            if 10 <= decade <= 90:
                ranges.append((decade, decade + 9))
        return ranges

    def _ranges_overlap(self, first: tuple[int, int], second: tuple[int, int]) -> bool:
        return first[0] <= second[1] and second[0] <= first[1]

    def _contains_any(self, text: str, terms: tuple[str, ...]) -> bool:
        return any(self._contains_phrase(text, term) for term in terms)

    def _contains_phrase(self, text: str, phrase: str) -> bool:
        pattern = r"(?<![a-z])" + re.escape(phrase.lower()) + r"(?![a-z])"
        return bool(re.search(pattern, text))
