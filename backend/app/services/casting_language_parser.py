from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


BILLING_TERMS = {
    "series regular": "Series Regular",
    "recurring guest star": "Recurring Guest Star",
    "guest star": "Guest Star",
    "co-star": "Co-Star",
    "costar": "Co-Star",
    "lead": "Lead",
    "supporting": "Supporting",
    "principal": "Principal",
    "day player": "Day Player",
    "under five": "Under Five",
    "u/5": "Under Five",
    "featured": "Featured",
    "background": "Background",
    "extra": "Extra",
    "ensemble": "Ensemble",
    "swing": "Swing",
    "standby": "Standby",
    "voiceover": "Voiceover",
    "vo": "Voiceover",
    "commercial principal": "Commercial Principal",
}

GENDER_TERMS = {
    "female presenting": "Female Presenting",
    "woman": "Woman",
    "women": "Woman",
    "female": "Female",
    "male presenting": "Male Presenting",
    "man": "Man",
    "men": "Man",
    "male": "Male",
    "non-binary": "Non-Binary",
    "nonbinary": "Non-Binary",
    "gender nonconforming": "Gender Nonconforming",
    "open gender": "Open Gender",
    "any gender": "Any Gender",
    "all genders": "All Genders",
}

ETHNICITY_TERMS = {
    "any ethnic appearance": "Any Ethnic Appearance",
    "any ethnicity": "Any Ethnicity",
    "all ethnicities": "All Ethnicities",
    "open ethnicity": "Open Ethnicity",
    "ethnically ambiguous": "Ethnically Ambiguous",
    "black": "Black",
    "african american": "African American",
    "african descent": "African Descent",
    "latina": "Latina",
    "latino": "Latino",
    "latinx": "Latinx",
    "hispanic": "Hispanic",
    "asian": "Asian",
    "south asian": "South Asian",
    "east asian": "East Asian",
    "middle eastern": "Middle Eastern",
    "white": "White",
    "caucasian": "White",
    "indigenous": "Indigenous",
    "native american": "Native American",
    "mixed race": "Mixed Race",
}

UNION_TERMS = {
    "sag-aftra": "SAG-AFTRA",
    "sag": "SAG-AFTRA",
    "aftra": "SAG-AFTRA",
    "aea": "AEA",
    "equity": "AEA",
    "non-union": "Non-Union",
    "non union": "Non-Union",
    "nu": "Non-Union",
    "union": "Union",
}

COMPENSATION_PATTERNS = [
    re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?(?:\s?[/a-zA-Z]+)?", flags=re.I),
    re.compile(r"\b(?:paid|deferred|copy credit meals|copy/credit/meals|stipend|no pay|unpaid)\b", flags=re.I),
]


@dataclass(frozen=True)
class CastingLanguageParse:
    original_text: str
    billing: str | None
    age_range: str | None
    gender: str | None
    ethnicity: str | None
    union: str | None
    compensation: str | None
    special_notes: list[str]

    def model_data(self) -> dict[str, Any]:
        return {
            "original_text": self.original_text,
            "billing": self.billing,
            "age_range": self.age_range,
            "gender": self.gender,
            "ethnicity": self.ethnicity,
            "union": self.union,
            "compensation": self.compensation,
            "special_notes": self.special_notes,
        }


class CastingLanguageParser:
    """Parse compact casting shorthand without replacing the original phrase."""

    def parse(self, text: str | None) -> CastingLanguageParse | None:
        original = " ".join(str(text or "").split()).strip()
        if not original:
            return None
        parts = [part.strip() for part in re.split(r"\s+/\s+|\s*(?:\||•|;)\s*", original) if part.strip()]
        candidates = parts or [original]
        used: set[str] = set()
        billing = self._match_dictionary(candidates, BILLING_TERMS, used)
        age_range = self._age_range(candidates, used)
        gender = self._match_dictionary(candidates, GENDER_TERMS, used)
        ethnicity = self._match_dictionary(candidates, ETHNICITY_TERMS, used)
        union = self._match_dictionary(candidates, UNION_TERMS, used)
        compensation = self._compensation(candidates, used)
        special_notes = [part for index, part in enumerate(candidates) if str(index) not in used]
        if not any([billing, age_range, gender, ethnicity, union, compensation, special_notes]):
            return None
        return CastingLanguageParse(
            original_text=original,
            billing=billing,
            age_range=age_range,
            gender=gender,
            ethnicity=ethnicity,
            union=union,
            compensation=compensation,
            special_notes=special_notes,
        )

    def parse_role(self, role: dict[str, Any]) -> CastingLanguageParse | None:
        explicit = role.get("casting_language") or role.get("casting_shorthand")
        if explicit:
            return self.parse(str(explicit))
        fields = [
            role.get("billing") or role.get("role_type"),
            role.get("age_range"),
            role.get("gender_presentation"),
            role.get("ethnicity"),
            role.get("union_status"),
            role.get("compensation"),
        ]
        joined = " / ".join(str(value) for value in fields if value)
        parsed = self.parse(joined)
        if parsed:
            return parsed
        return self.parse(role.get("role_requirement_text"))

    def _match_dictionary(self, candidates: list[str], dictionary: dict[str, str], used: set[str]) -> str | None:
        for index, candidate in enumerate(candidates):
            lowered = self._normalize(candidate)
            for key, label in dictionary.items():
                if lowered == key or re.search(rf"\b{re.escape(key)}\b", lowered):
                    used.add(str(index))
                    return label
        return None

    def _age_range(self, candidates: list[str], used: set[str]) -> str | None:
        patterns = [
            re.compile(r"\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\b"),
            re.compile(r"\b(?:reads?|plays?|age|ages)\s*(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\b", flags=re.I),
            re.compile(r"\b(?:late|mid|early)\s+(?:teens|20s|30s|40s|50s|60s)\b", flags=re.I),
            re.compile(r"\b\d{1,2}s\b"),
        ]
        for index, candidate in enumerate(candidates):
            for pattern in patterns:
                match = pattern.search(candidate)
                if match:
                    used.add(str(index))
                    return match.group(0)
        return None

    def _compensation(self, candidates: list[str], used: set[str]) -> str | None:
        for index, candidate in enumerate(candidates):
            for pattern in COMPENSATION_PATTERNS:
                match = pattern.search(candidate)
                if match:
                    used.add(str(index))
                    return match.group(0)
        return None

    def _normalize(self, value: str) -> str:
        return re.sub(r"\s+", " ", value.strip().lower())
