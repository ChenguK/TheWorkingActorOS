from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import BreakdownRole, CharacterProfile, Opportunity


ARCHETYPE_RULES = [
    {
        "label": "Mom",
        "terms": ["mom", "mother", "parent", "her child", "her kids", "family"],
        "base": 68,
    },
    {
        "label": "Protective Mother",
        "terms": ["protect", "protective", "defend", "child", "children", "family", "mother", "mom"],
        "requires_any": ["protect", "protective", "defend", "child", "children"],
        "base": 78,
    },
    {
        "label": "PTA Mom",
        "terms": ["pta", "school", "teacher", "principal", "community", "committee", "suburban", "parent"],
        "base": 72,
    },
    {
        "label": "Warm Authority",
        "terms": ["warm", "authority", "leader", "organized", "commanding", "principal", "teacher", "nurturing"],
        "base": 76,
    },
    {
        "label": "Middle-Class Parent",
        "terms": ["middle-class", "middle class", "suburban", "home", "family", "parent", "pta", "neighborhood"],
        "base": 72,
    },
    {
        "label": "Emotional Caregiver",
        "terms": ["caregiver", "nurturing", "supportive", "emotional", "comfort", "protect", "mother", "nurse"],
        "base": 70,
    },
    {
        "label": "Romantic Optimist",
        "terms": ["romantic", "optimist", "hopeful", "love", "believes in love", "dating", "heart"],
        "base": 70,
    },
    {
        "label": "Supporting Character",
        "terms": ["supporting", "supportive", "friend", "neighbor", "co-worker", "coworker", "sidekick"],
        "base": 66,
    },
    {
        "label": "Authority Figure",
        "terms": ["authority", "commanding", "leader", "principal", "administrator", "judge", "dean"],
        "base": 74,
    },
    {"label": "Attorney", "terms": ["attorney", "lawyer", "legal", "court", "prosecutor", "defense"], "base": 82},
    {"label": "Detective", "terms": ["detective", "investigator", "federal agent", "case", "procedural"], "base": 82},
    {"label": "Executive", "terms": ["executive", "ceo", "director", "corporate", "boss"], "base": 78},
    {"label": "Medical Professional", "terms": ["nurse", "doctor", "hospital", "medical", "clinic"], "base": 78},
    {"label": "Journalist", "terms": ["journalist", "reporter", "newsroom", "investigative"], "base": 78},
    {"label": "Teacher", "terms": ["teacher", "professor", "educator", "classroom"], "base": 76},
    {"label": "Parent", "terms": ["mother", "mom", "parent", "family loyalty", "father"], "base": 70},
    {"label": "Best Friend", "terms": ["best friend", "friend", "confidante"], "base": 70},
    {"label": "Comedy", "terms": ["comedy", "comedic", "funny", "witty", "scene-stealer", "sitcom"], "base": 72},
    {
        "label": "Dramatic Guest Star",
        "terms": ["dramatic", "emotional", "vulnerable", "grief", "survival", "high stakes"],
        "base": 72,
    },
    {"label": "Survivor", "terms": ["survival", "resilient", "hardened", "circumstance", "autonomy"], "base": 76},
    {"label": "Fighter", "terms": ["fight", "fighter", "martial", "judo", "grappling", "mma", "stage combat"], "base": 78},
    {"label": "Political Leader", "terms": ["political", "campaign", "senator", "mayor", "staffer"], "base": 78},
    {
        "label": "Musical Theater",
        "terms": ["musical", "vocalist", "belt", "tenor", "baritone", "soprano", "alto"],
        "base": 76,
    },
]


class CharacterIntelligenceEngine:
    """Infer character-facing acting intelligence from parsed role text."""

    VERSION = "character-intelligence-v1"

    def __init__(self, db: Session | None = None) -> None:
        self.db = db

    def run_for_opportunity(self, opportunity: Opportunity) -> None:
        for role in opportunity.breakdown_roles:
            profile_data = self.profile_for_role(role, opportunity)
            existing = role.character_profile
            if existing is None:
                profile = CharacterProfile(
                    breakdown=opportunity,
                    breakdown_role=role,
                    **profile_data,
                )
                role.character_profile = profile
                if self.db:
                    self.db.add(profile)
            else:
                for key, value in profile_data.items():
                    setattr(existing, key, value)
        if self.db:
            self.db.flush()

    def profile_for_role(self, role: BreakdownRole, opportunity: Opportunity | None = None) -> dict[str, Any]:
        text = self._role_text(role, opportunity)
        archetype_scores = self._archetype_scores(text, role)
        primary_archetypes = [item["archetype"] for item in archetype_scores if item["tier"] == "Primary"]
        secondary_archetypes = [item["archetype"] for item in archetype_scores if item["tier"] == "Secondary"]
        archetypes = [*primary_archetypes, *secondary_archetypes]
        traits = self._traits(text)
        emotional_traits = self._emotional_traits(text)
        relationships = self._relationships(text)
        motivations = self._motivations(text)
        genre = self._genre(text, opportunity)
        physical_requirements = self._requirements(
            [role.height_requirements, role.special_skills],
            text,
            ["height", "athletic", "physical", "fight", "combat", "martial", "grappling", "MMA", "judo"],
        )
        vocal_requirements = self._requirements(
            [role.vocal_requirements],
            text,
            ["vocal", "singer", "tenor", "baritone", "belt", "mezzo", "soprano", "alto", "musical"],
        )
        movement_requirements = self._requirements(
            [role.dance_requirements, role.movement_requirements],
            text,
            ["movement", "dance", "choreography", "stage combat", "physical storytelling", "athletic"],
        )
        casting_language = self._casting_language(text)
        comedic_level = self._level(text, ["comedy", "comedic", "funny", "witty", "farce", "sitcom", "scene-stealer"])
        dramatic_level = self._level(
            text,
            ["drama", "dramatic", "emotional", "grief", "survival", "vulnerable", "trauma", "conflict", "procedural"],
            default=45,
        )
        return {
            "role_name": role.role_name,
            "billing": role.billing or role.billing_or_role_type or role.role_type,
            "primary_archetypes": primary_archetypes,
            "secondary_archetypes": secondary_archetypes,
            "archetype_confidence_scores": archetype_scores,
            "personality_traits": traits,
            "emotional_traits": emotional_traits,
            "relationships": relationships,
            "motivations": motivations,
            "internal_conflict": self._internal_conflict(text),
            "external_conflict": self._external_conflict(text),
            "emotional_arc": self._emotional_arc(text),
            "genre": genre,
            "comedic_level": comedic_level,
            "dramatic_level": dramatic_level,
            "physical_requirements": physical_requirements,
            "vocal_requirements": vocal_requirements,
            "movement_requirements": movement_requirements,
            "casting_language": casting_language,
            "recommended_materials": self._recommended_materials(archetypes, genre, vocal_requirements, movement_requirements),
            "ai_summary": self._summary(role, archetypes, traits, emotional_traits, genre, comedic_level, dramatic_level),
        }

    def _role_text(self, role: BreakdownRole, opportunity: Opportunity | None = None) -> str:
        values = [
            role.role_name,
            role.billing,
            role.role_type,
            role.character_description,
            role.role_notes,
            role.vocal_requirements,
            role.dance_requirements,
            role.movement_requirements,
            role.language_requirements,
            role.special_skills,
        ]
        if opportunity:
            values.extend(
                [
                    opportunity.project_type,
                    opportunity.role_type,
                    opportunity.description,
                    opportunity.ai_summary,
                    (opportunity.production_details or {}).get("project_type"),
                    (opportunity.role_details or {}).get("tone"),
                ]
            )
        return "\n".join(str(value) for value in values if value)

    def _archetype_scores(self, text: str, role: BreakdownRole) -> list[dict[str, Any]]:
        lowered = text.lower()
        scored = []
        for rule in ARCHETYPE_RULES:
            evidence = [term for term in rule["terms"] if self._contains_phrase(lowered, term)]
            required = rule.get("requires_any")
            if required and not any(self._contains_phrase(lowered, term) for term in required):
                continue
            if not evidence:
                continue
            confidence = min(95, int(rule["base"]) + (len(evidence) - 1) * 5)
            scored.append(
                {
                    "archetype": rule["label"],
                    "confidence": confidence,
                    "tier": "Primary" if confidence >= 74 else "Secondary",
                    "evidence": evidence[:6],
                }
            )
        scored = self._add_contextual_archetypes(scored, lowered, role)
        scored.sort(key=lambda item: (-int(item["confidence"]), str(item["archetype"])))
        return scored[:12]

    def _add_contextual_archetypes(self, scored: list[dict[str, Any]], lowered: str, role: BreakdownRole) -> list[dict[str, Any]]:
        existing = {item["archetype"] for item in scored}
        role_type = " ".join(str(item or "") for item in [role.billing, role.role_type, role.billing_or_role_type]).lower()
        additions = []
        if "supporting" in role_type and "Supporting Character" not in existing:
            additions.append(("Supporting Character", 68, ["supporting billing"]))
        if any(term in lowered for term in ["warm", "nurturing", "kind"]) and "Warm Authority" in existing and "Emotional Caregiver" not in existing:
            additions.append(("Emotional Caregiver", 70, ["warm/nurturing character energy"]))
        if "mom" in lowered or "mother" in lowered:
            for label, confidence, evidence in [
                ("Protective Mother", 78, ["mother/parent protective lane"]),
                ("Middle-Class Parent", 70, ["parent casting lane"]),
            ]:
                if label not in existing:
                    additions.append((label, confidence, evidence))
        for label, confidence, evidence in additions:
            scored.append(
                {
                    "archetype": label,
                    "confidence": confidence,
                    "tier": "Primary" if confidence >= 74 else "Secondary",
                    "evidence": evidence,
                }
            )
        return scored

    def _traits(self, text: str) -> list[str]:
        rules = [
            ("confident", ["confident", "commanding", "bold"]),
            ("charismatic", ["charismatic", "magnetic"]),
            ("disciplined", ["disciplined", "focused"]),
            ("ambitious", ["ambition", "ambitious", "hunger", "dream"]),
            ("resilient", ["resilient", "survival"]),
            ("proud", ["proud"]),
            ("stubborn", ["stubborn"]),
            ("instinctive", ["instinctive", "instinct"]),
            ("sensitive", ["sensitive", "vulnerable"]),
            ("authoritative", ["authority", "leader", "commanding"]),
            ("warm", ["warm", "lovable", "humanity"]),
        ]
        return self._matched_labels(text, rules)

    def _emotional_traits(self, text: str) -> list[str]:
        rules = [
            ("emotionally available", ["emotional range", "connect deeply", "sensitive"]),
            ("guarded", ["hardened", "survival", "circumstance"]),
            ("vulnerable", ["vulnerable", "vulnerability"]),
            ("intense", ["intensity", "charged", "threatens"]),
            ("resolute", ["dignity", "autonomy", "resilient"]),
            ("playful", ["comedy", "witty", "funny"]),
        ]
        return self._matched_labels(text, rules)

    def _relationships(self, text: str) -> list[str]:
        rules = [
            ("family", ["family", "mother", "father", "daughter", "son", "sibling"]),
            ("romantic connection", ["romantic", "relationship", "sensuality", "charged"]),
            ("workplace authority", ["boss", "office", "executive", "administrator"]),
            ("mentor/student", ["teacher", "student", "coach", "mentor"]),
            ("patient/caregiver", ["patient", "nurse", "doctor", "caregiver"]),
            ("community", ["community", "immigration", "identity"]),
            ("professional colleague", ["colleague", "partner", "associate"]),
        ]
        return self._matched_labels(text, rules)

    def _motivations(self, text: str) -> list[str]:
        rules = [
            ("autonomy", ["autonomy", "define herself", "right to define"]),
            ("recognition", ["recognition", "seen", "respect"]),
            ("dignity", ["dignity"]),
            ("survival", ["survival", "survive"]),
            ("justice", ["justice", "truth", "legal"]),
            ("ambition", ["ambition", "dream", "hunger"]),
            ("family loyalty", ["family loyalty", "family"]),
            ("love or connection", ["connect deeply", "relationship", "love"]),
        ]
        return self._matched_labels(text, rules)

    def _internal_conflict(self, text: str) -> str | None:
        lowered = text.lower()
        if "survival" in lowered and ("vulnerab" in lowered or "sensitive" in lowered):
            return "Balancing survival instincts with emotional vulnerability."
        if "ambition" in lowered and "family" in lowered:
            return "Ambition presses against loyalty and belonging."
        if "identity" in lowered or "define herself" in lowered:
            return "A need to define identity on personal terms."
        if "dream" in lowered and ("threatens" in lowered or "fascinates" in lowered):
            return "The character wants a dream but is emotionally unsettled by another person's power."
        return None

    def _external_conflict(self, text: str) -> str | None:
        lowered = text.lower()
        if "systems of power" in lowered or "gender expectations" in lowered:
            return "Pressure from systems of power, gender expectations, and social limits."
        if "immigration" in lowered:
            return "External pressure connected to immigration, culture, and identity."
        if "court" in lowered or "legal" in lowered:
            return "Professional stakes inside a legal or procedural environment."
        if "family loyalty" in lowered:
            return "Family expectations complicate the character's choices."
        return None

    def _emotional_arc(self, text: str) -> str | None:
        lowered = text.lower()
        if "journey" in lowered or "evolution" in lowered or "confronting" in lowered:
            return "The role appears to move through confrontation, self-definition, and emotional change."
        if "dream" in lowered and "relationship" in lowered:
            return "The role likely shifts as ambition and intimacy collide."
        if "survival" in lowered and "dignity" in lowered:
            return "The role likely moves from defense toward dignity and agency."
        return None

    def _genre(self, text: str, opportunity: Opportunity | None) -> str | None:
        combined = f"{text} {getattr(opportunity, 'project_type', '') or ''}".lower()
        if "musical" in combined:
            return "Musical Theater"
        if "theater" in combined or "stage" in combined or "play" in combined:
            return "Theater"
        if "procedural" in combined or "detective" in combined:
            return "Procedural Drama"
        if "comedy" in combined or "sitcom" in combined:
            return "Comedy"
        if "commercial" in combined:
            return "Commercial"
        if "voiceover" in combined or "voice over" in combined:
            return "Voiceover"
        if "drama" in combined:
            return "Drama"
        return getattr(opportunity, "project_type", None) if opportunity else None

    def _requirements(self, explicit_values: list[str | None], text: str, terms: list[str]) -> list[str]:
        values = [str(value).strip() for value in explicit_values if value and str(value).strip()]
        values.extend(self._sentences_with_terms(text, terms))
        return self._unique(values)[:6]

    def _casting_language(self, text: str) -> list[str]:
        terms = [
            "seeking",
            "should read",
            "female",
            "male",
            "presenting",
            "vocalist",
            "tenor",
            "baritone",
            "belt",
            "requires",
            "must",
            "comfort",
            "experience",
            "plus",
        ]
        return self._sentences_with_terms(text, terms)[:8]

    def _recommended_materials(
        self,
        archetypes: list[str],
        genre: str | None,
        vocal_requirements: list[str],
        movement_requirements: list[str],
    ) -> list[str]:
        recommendations = []
        if any(item in archetypes for item in ["Authority Figure", "Attorney", "Executive", "Detective"]):
            recommendations.append("Authority-forward headshot")
            recommendations.append("Procedural or professional reel clip")
        if any(item in archetypes for item in ["Mom", "Protective Mother", "PTA Mom", "Middle-Class Parent"]):
            recommendations.append("Parent / warm family headshot")
            recommendations.append("Parenting or family-stakes scene")
        if "Warm Authority" in archetypes:
            recommendations.append("Warm authority headshot")
            recommendations.append("Professional-but-approachable reel clip")
        if "Emotional Caregiver" in archetypes:
            recommendations.append("Emotionally grounded caregiving scene")
        if "Romantic Optimist" in archetypes:
            recommendations.append("Romantic comedy or hopeful relationship scene")
        if "Supporting Character" in archetypes:
            recommendations.append("Supportive scene partner clip")
        if "Comedy" in archetypes:
            recommendations.append("Comedy clip or light conversational scene")
        if genre == "Musical Theater" or vocal_requirements:
            recommendations.append("Vocal reel or musical theater selection")
        if movement_requirements or "Fighter" in archetypes:
            recommendations.append("Movement, dance, or physical storytelling sample")
        if not recommendations:
            recommendations.append("Current headshot and strongest role-aligned reel")
        return self._unique(recommendations)

    def _summary(
        self,
        role: BreakdownRole,
        archetypes: list[str],
        traits: list[str],
        emotional_traits: list[str],
        genre: str | None,
        comedic_level: int,
        dramatic_level: int,
    ) -> str:
        tone = "dramatic" if dramatic_level >= comedic_level else "comedic"
        if dramatic_level >= 70 and comedic_level >= 70:
            tone = "heightened comedic and dramatic"
        archetype_text = ", ".join(archetypes[:3]) if archetypes else "role-specific"
        trait_text = ", ".join((traits + emotional_traits)[:4]) if traits or emotional_traits else "clear acting choices"
        return (
            f"{role.role_name} reads as a {tone} {genre or 'character'} role. "
            f"Likely archetypes: {archetype_text}. Acting strengths needed: {trait_text}."
        )

    def _level(self, text: str, terms: list[str], default: int = 25) -> int:
        lowered = text.lower()
        matches = sum(1 for term in terms if term in lowered)
        if matches >= 3:
            return 85
        if matches == 2:
            return 70
        if matches == 1:
            return 55
        return default

    def _sentences_with_terms(self, text: str, terms: list[str]) -> list[str]:
        sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
        matches = []
        for sentence in sentences:
            clean = " ".join(sentence.split()).strip()
            if not clean:
                continue
            lowered = clean.lower()
            if any(term.lower() in lowered for term in terms):
                matches.append(clean)
        return self._unique(matches)

    def _matched_labels(self, text: str, rules: list[tuple[str, list[str]]]) -> list[str]:
        lowered = text.lower()
        return [label for label, terms in rules if any(term.lower() in lowered for term in terms)]

    def _contains_phrase(self, text: str, phrase: str) -> bool:
        phrase = phrase.lower()
        if re.search(r"^[a-z0-9 ]+$", phrase):
            pattern = r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])"
            return bool(re.search(pattern, text))
        return phrase in text

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        unique = []
        for value in values:
            normalized = re.sub(r"\s+", " ", str(value).strip())
            key = normalized.lower()
            if normalized and key not in seen:
                seen.add(key)
                unique.append(normalized)
        return unique
