from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    category: str
    proficiency: str | None = None


class SkillParserService:
    CATEGORY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
        (
            "Dance",
            (
                "dance",
                "dancer",
                "ballroom",
                "swing",
                "tango",
                "tap",
                "modern",
                "ballet",
                "jazz",
                "hip hop",
                "salsa",
            ),
        ),
        (
            "Singing / Vocal",
            (
                "sing",
                "singer",
                "vocal",
                "alto",
                "soprano",
                "mezzo",
                "contralto",
                "baritone",
                "tenor",
                "belt",
                "belter",
            ),
        ),
        (
            "Sports / Athletics",
            (
                "aerobics",
                "billiards",
                "pool player",
                "combat",
                "stage combat",
                "cycling",
                "bike",
                "roller skating",
                "roller skate",
                "rollerblading",
                "running",
                "sprint",
                "soccer",
                "swimming",
                "swim",
                "volleyball",
                "yoga",
                "martial",
                "athletic",
            ),
        ),
        (
            "Accents / Dialects",
            (
                "accent",
                "dialect",
                "kenyan",
                "southern",
                "southern american",
                "english",
                "british",
                "bbc english",
                "scouse",
                "liverpool",
                "valley girl",
                "new york",
                "new yorker",
                "boston",
                "standard american",
                "american southern",
                "west african",
                "african",
                "standard",
                "general",
            ),
        ),
        ("Voiceover", ("voiceover", "voice over", "vo")),
        ("Music / Instruments", ("violin", "piano", "guitar", "drums", "instrument")),
        ("Modeling / Print", ("modeling", "model", "commercial print", "print")),
        ("Professional / Technical", ("software", "coding", "teleprompter", "medical equip", "photography")),
        ("Licenses / Documents", ("passport", "driver", "drivers", "driver's license", "license")),
        ("Creative / Domestic", ("sew", "knit", "crochet", "cook", "bake")),
    )

    ACCENT_PREFIXES = (
        "American - ",
        "British - ",
    )

    def parse_text(self, text: str) -> list[ParsedSkill]:
        return self.parse_items(self._split_items(text))

    def parse_items(self, items: list[str]) -> list[ParsedSkill]:
        parsed: list[ParsedSkill] = []
        seen: set[tuple[str, str]] = set()
        for item in items:
            split_items = self._split_items(item) if re.search(r"[,;|]", item) else [item]
            for split_item in split_items:
                for expanded in self._expand_item(split_item):
                    name = self._clean_name(expanded)
                    if not name or self._is_measurement(name):
                        continue
                    category = self.category_for(name)
                    proficiency = self._proficiency_for(name)
                    key = (name.lower(), category)
                    if key in seen:
                        continue
                    seen.add(key)
                    parsed.append(ParsedSkill(name=name, category=category, proficiency=proficiency))
        return parsed

    def parse_items_without_splitting(self, items: list[str]) -> list[ParsedSkill]:
        parsed: list[ParsedSkill] = []
        seen: set[tuple[str, str]] = set()
        for item in items:
            for expanded in self._expand_item(item):
                name = self._clean_name(expanded)
                if not name or self._is_measurement(name):
                    continue
                category = self.category_for(name)
                proficiency = self._proficiency_for(name)
                key = (name.lower(), category)
                if key in seen:
                    continue
                seen.add(key)
                parsed.append(ParsedSkill(name=name, category=category, proficiency=proficiency))
        return parsed

    def category_for(self, skill: str) -> str:
        lowered = skill.lower()
        for category, patterns in self.CATEGORY_PATTERNS:
            if any(pattern in lowered for pattern in patterns):
                return category
        return "Special Skill"

    def actor_skills(self, parsed: list[ParsedSkill]) -> list[str]:
        return [skill.name for skill in parsed if skill.category != "Accents / Dialects"]

    def accents(self, parsed: list[ParsedSkill]) -> list[str]:
        return [skill.name for skill in parsed if skill.category == "Accents / Dialects"]

    def grouped(self, parsed: list[ParsedSkill]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for skill in parsed:
            grouped.setdefault(skill.category, []).append(skill.name)
        return grouped

    def _split_items(self, value: str) -> list[str]:
        normalized = value.replace("\n", ",")
        normalized = re.sub(r"\bDialects:\s*", "", normalized, flags=re.I)
        return [item.strip(" .") for item in re.split(r"[,;|]", normalized) if item.strip(" .")]

    def _expand_item(self, item: str) -> list[str]:
        stripped = item.strip()
        if not stripped:
            return []
        if re.match(r"^(Vocal Range|Vocal Style):", stripped, flags=re.I):
            return [stripped]
        for prefix in self.ACCENT_PREFIXES:
            if stripped.startswith(prefix):
                return [stripped]
        return [stripped]

    def _clean_name(self, value: str) -> str:
        value = re.sub(r"\s+", " ", value.strip(" ."))
        replacements = {
            "Bike ride": "Bike Riding",
            "Swim": "Swimming",
            "PA State Drivers' License": "PA State Driver's License",
            "PA State Drivers’ License": "PA State Driver's License",
            "American - Standard/General Accent": "American - Standard/General Accent",
            "British - BBC English Accent": "British RP / BBC English Accent",
        }
        return replacements.get(value, value)

    def _is_measurement(self, value: str) -> bool:
        return bool(re.match(r"^(height|weight)\s*:", value, flags=re.I))

    def _proficiency_for(self, value: str) -> str | None:
        lowered = value.lower()
        if "ability - general" in lowered:
            return "General"
        if "licensed" in lowered or "license" in lowered:
            return "Licensed"
        return None
