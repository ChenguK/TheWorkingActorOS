from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.automation.discovery.classification import classify_breakdown_text


ROLE_HEADING_PATTERN = re.compile(
    r"^(?P<name>[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ' .-]{1,80})\s*\((?P<type>lead|principal|supporting|featured|ensemble|chorus|understudy|swing|role)\)$",
    flags=re.I,
)
ROLE_COLON_PATTERN = re.compile(
    r"^(?P<name>[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ0-9' .-]{1,80})\s*:\s*(?:\[(?P<requirements>[^\]]+)\])?\s*$",
)
GENDER_TERMS = ("Female", "Male", "Woman", "Man", "Nonbinary", "Non-binary", "Trans")
REQUIREMENT_KEYWORDS = (
    "female",
    "male",
    "should read",
    "seeking",
    "vocalist",
    "tenor",
    "baritone",
    "soprano",
    "alto",
    "dance",
    "movement",
    "martial arts",
    "stage combat",
    "language",
    "portuguese",
    "spanish",
    "guitar",
)


class BreakdownDetailsService:
    def from_fields(
        self,
        *,
        role: str,
        project: str,
        union: str,
        location: str,
        description: str,
        source_name: str | None = None,
        source_url: str | None = None,
        source_type: str | None = None,
        platform: str | None = None,
        import_method: str | None = None,
        discovered_at: str | None = None,
        category: str | None = None,
        role_type: str | None = None,
        project_type: str | None = None,
        archetypes: list[str] | None = None,
        audition_type: str | None = None,
        rate: str | None = None,
        shoot_location: str | None = None,
        audition_location: str | None = None,
        travel_covered: bool | None = None,
        housing_covered: bool | None = None,
        shoot_dates: str | None = None,
        submission_deadline: str | None = None,
        audition_deadline: str | None = None,
        callback_info: str | None = None,
        raw_visible_text: str | None = None,
    ) -> dict[str, Any]:
        text = raw_visible_text or description
        parsed = self.from_text(text)
        source_metadata = self._clean_dict(
            {
                **parsed["source_metadata"],
                "source_platform": platform or source_name,
                "source_url": source_url,
                "source_type": source_type,
                "provider_name": source_name,
                "import_method": import_method,
                "discovered_at": discovered_at or datetime.now(timezone.utc).isoformat(),
            }
        )
        production_details = self._clean_dict(
            {
                **parsed["production_details"],
                "project_title": project,
                "project_type": project_type or parsed["production_details"].get("project_type") or category,
                "union_status": union,
                "shoot_location": shoot_location or location,
                "shoot_dates": shoot_dates,
                "rate": rate,
                "travel_provided": self._yes_no(travel_covered),
                "housing_provided": self._yes_no(housing_covered),
            }
        )
        role_details = self._clean_dict(
            {
                **parsed["role_details"],
                "role_name": role,
                "role_type": role_type or parsed["role_details"].get("role_type"),
                "character_description": parsed["role_details"].get("character_description")
                or self._actor_facing_description(text, role),
                "archetypes": archetypes or [],
                "audition_type": audition_type,
                "audition_location": audition_location,
                "self_tape_due_date": submission_deadline or audition_deadline,
                "callback_info": callback_info,
            }
        )
        submission_instructions = parsed["submission_instructions"] or self._field_from_text(
            text, ["submission", "submit", "instructions", "to submit"]
        )
        ai_summary = self._summary(production_details, role_details, submission_instructions)
        return {
            "source_metadata": source_metadata,
            "production_details": production_details,
            "role_details": role_details,
            "extracted_facts": parsed.get("extracted_facts", {}),
            "ai_inference": parsed.get("ai_inference", {}),
            "submission_instructions": submission_instructions,
            "ai_summary": ai_summary,
        }

    def from_text(self, text: str) -> dict[str, Any]:
        cleaned = self._clean_text(text)
        lines = [line.strip() for line in re.split(r"[\n\r]+", cleaned) if line.strip()]
        joined = " ".join(lines)
        classification = classify_breakdown_text(joined)
        is_theater = self._is_theater(joined)
        is_epa = self._is_epa(joined)
        audition_date, audition_time = self._extract_audition_date_time(lines)
        date_facts = self._extract_date_facts(lines)
        audition_location_name, audition_address = self._extract_location(lines, ["location", "audition location"])
        preparation = self._section_text(lines, ["preparation", "prepare"])
        project_type = self._project_type(joined)
        production_details = self._clean_dict(
            {
                "project_title": self._field(lines, ["project", "production", "title"]),
                "production_company": self._field(lines, ["production company", "producer"]),
                "network_platform": self._field(lines, ["network", "platform", "distributor"]),
                "director": self._field(lines, ["director"]),
                "casting_office": self._field(lines, ["casting office", "casting", "casting director"]),
                "project_type": project_type,
                "union_status": self._find_known(joined, ["SAG-AFTRA", "SAG", "AEA", "Equity", "Non-Union", "Union"]),
                "shoot_location": None if is_theater else self._field(lines, ["shoot location", "location", "works", "work location"]),
                "shoot_dates": None if is_theater else self._field(lines, ["shoot dates", "shoot date", "work dates", "rehearsal"]),
                "submission_deadline": date_facts.get("submission_deadline"),
                "expiration_date": date_facts.get("expiration_date"),
                "work_dates": date_facts.get("shoot_or_work_dates"),
                "shooting_location": None if is_theater else self._field(lines, ["shoot location", "shooting location", "works", "work location"]),
                "performance_location": self._field(lines, ["performance location", "performance venue", "venue"]) if is_theater else None,
                "rehearsal_location": self._field(lines, ["rehearsal location", "rehearses"]) if is_theater else None,
                "audition_location_name": audition_location_name if is_theater else None,
                "audition_address": audition_address if is_theater else None,
                "audition_date": audition_date if is_theater else None,
                "audition_time": audition_time if is_theater else None,
                "preparation": preparation if is_theater else None,
                "rate": self._field(lines, ["rate", "pay", "salary", "compensation"]),
                "travel_housing": self._field(lines, ["travel", "housing", "lodging"]),
            }
        )
        if is_theater:
            production_details["shooting_location"] = None
        role_details = self._clean_dict(
            {
                "role_name": self._field(lines, ["role", "character"]),
                "role_type": self._field(lines, ["role type", "billing"]),
                "character_description": self._description(lines),
                "age_range": self._field(lines, ["age", "age range", "playable age"]),
                "gender_presentation": self._field(lines, ["gender", "gender presentation"]),
                "ethnicity": self._field(lines, ["ethnicity", "race"]),
                "skills_required": self._field(lines, ["skills", "special skills"]),
                "wardrobe_physical_requirements": self._field(lines, ["wardrobe", "physical", "requirements"]),
                "audition_type": self._audition_type(joined),
                "audition_subtype": "EPA" if is_epa else None,
                "audition_date": audition_date if is_theater else None,
                "audition_time": audition_time if is_theater else None,
                "audition_location_name": audition_location_name if is_theater else None,
                "audition_address": audition_address if is_theater else None,
                "preparation": preparation,
                "self_tape_due_date": self._field(lines, ["self tape due", "self-tape due", "deadline", "due date"]),
                "submission_deadline": date_facts.get("submission_deadline"),
                "expiration_date": date_facts.get("expiration_date"),
                "callback_info": self._field(lines, ["callback", "callback date"]),
                "breakdown_classification": classification.classification,
            }
        )
        available_roles = self._role_blocks(lines)
        if available_roles:
            first_role = available_roles[0]
            role_details = self._clean_dict(
                {
                    **role_details,
                    "role_name": role_details.get("role_name") or first_role.get("role_name"),
                    "role_type": role_details.get("role_type") or first_role.get("role_type"),
                    "character_description": first_role.get("character_description") or role_details.get("character_description"),
                    "age_range": role_details.get("age_range") or first_role.get("age_range"),
                    "gender_presentation": role_details.get("gender_presentation") or first_role.get("gender_presentation"),
                    "ethnicity": role_details.get("ethnicity") or first_role.get("ethnicity"),
                    "skills_required": role_details.get("skills_required") or first_role.get("skills_required"),
                    "wardrobe_physical_requirements": role_details.get("wardrobe_physical_requirements") or first_role.get("height_requirement"),
                    "available_roles": available_roles,
                }
            )
        submission_instructions = self._field(lines, ["submission", "submit", "instructions", "to submit"])
        extracted_facts = self._breakdown_extracted_facts(
            production_details=production_details,
            role_details=role_details,
            submission_instructions=submission_instructions,
            date_facts=date_facts,
        )
        ai_inference = self._breakdown_ai_inference(
            classification=classification.classification,
            role_details=role_details,
            production_details=production_details,
        )
        return {
            "source_metadata": {
                "parse_source": "manual_or_visible_text",
                "parsed_at": datetime.now(timezone.utc).isoformat(),
            },
            "production_details": production_details,
            "role_details": role_details,
            "extracted_facts": extracted_facts,
            "ai_inference": ai_inference,
            "submission_instructions": submission_instructions,
            "ai_summary": self._summary(production_details, role_details, submission_instructions),
            "breakdown_classification": classification.classification,
            "rejection_reason": classification.rejection_reason,
        }

    def _field(self, lines: list[str], labels: list[str]) -> str | None:
        for index, line in enumerate(lines):
            lower = line.lower().strip(":")
            for label in sorted(labels, key=len, reverse=True):
                if lower.startswith(label.lower()):
                    value = re.sub(rf"^{re.escape(label)}\s*:?\s*", "", line, flags=re.I).strip()
                    if value:
                        return value[:1000]
                    if index + 1 < len(lines):
                        return lines[index + 1][:1000]
        return None

    def _field_from_text(self, text: str, labels: list[str]) -> str | None:
        return self._field([part.strip() for part in re.split(r"[.;\n\r]+", text) if part.strip()], labels)

    def _find_known(self, text: str, values: list[str]) -> str | None:
        lower = text.lower()
        return next((value for value in values if value.lower() in lower), None)

    def _project_type(self, text: str) -> str | None:
        lower = text.lower()
        if self._is_epa(text):
            return "Theatre"
        if "musical" in lower or "musical theatre" in lower or "musical theater" in lower:
            return "Theater / Musical Theater"
        for value in ["Television", "Film", "Commercial", "Theater", "Voiceover", "New Media", "Streaming"]:
            if value.lower() in lower:
                return value
        return None

    def _audition_type(self, text: str) -> str:
        lower = text.lower()
        if self._is_epa(text):
            return "In-Person"
        if "self tape" in lower or "self-tape" in lower or "eco cast" in lower:
            return "Self-Tape"
        if "zoom" in lower or "virtual" in lower:
            return "Virtual"
        if "in-person" in lower or "in person" in lower or "epa" in lower or "ecc" in lower:
            return "In-Person"
        return "Unknown"

    def _is_epa(self, text: str) -> bool:
        return bool(re.search(r"\b(EPA|Equity Principal Audition)\b", text, flags=re.I))

    def _is_theater(self, text: str) -> bool:
        lower = text.lower()
        return self._is_epa(text) or bool(
            re.search(r"\b(theatre|theater|musical|play|stage|epa|equity principal audition|broadway|off-broadway)\b", lower)
        )

    def _section_text(self, lines: list[str], headings: list[str]) -> str | None:
        for index, line in enumerate(lines):
            normalized = line.lower().strip(":")
            if normalized not in [heading.lower() for heading in headings]:
                continue
            block: list[str] = []
            cursor = index + 1
            while cursor < len(lines) and not self._looks_like_section_heading(lines[cursor]):
                block.append(lines[cursor])
                cursor += 1
            return "\n".join(block).strip()[:3000] or None
        return None

    def _extract_audition_date_time(self, lines: list[str]) -> tuple[str | None, str | None]:
        date_value = self._section_text(lines, ["audition date"])
        if not date_value:
            date_value = self._field(lines, ["audition date", "audition"])
        if not date_value:
            return None, None
        date_lines = [line.strip() for line in date_value.splitlines() if line.strip()]
        date_line = next((line for line in date_lines if re.search(r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", line, flags=re.I)), date_lines[0])
        time_line = next((line for line in date_lines if re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\b", line, flags=re.I)), None)
        if not time_line:
            match = re.search(r"\b\d{1,2}:\d{2}\s*(?:AM|PM)\s*(?:-|–|to)\s*\d{1,2}:\d{2}\s*(?:AM|PM)\b", " ".join(date_lines), flags=re.I)
            time_line = match.group(0) if match else None
        date_match = re.search(
            r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})\b",
            date_line,
        )
        return (date_match.group(1) if date_match else date_line, time_line)

    def _extract_date_facts(self, lines: list[str]) -> dict[str, str]:
        facts: dict[str, str] = {}
        label_groups = {
            "posted_date": ["posted", "posted date", "date posted"],
            "submission_deadline": [
                "submission deadline",
                "submission due",
                "submit by",
                "deadline",
                "due date",
                "self tape due",
                "self-tape due",
                "tape due",
            ],
            "expiration_date": ["expires", "expiration", "expiration date", "listing expires"],
            "audition_date": ["audition date", "auditions", "epa date", "ecc date"],
            "callback_date": ["callback date", "callback"],
            "shoot_or_work_dates": ["shoot dates", "shoot date", "work dates", "performance dates", "rehearsal dates"],
        }
        for key, labels in label_groups.items():
            value = self._field(lines, labels)
            if value:
                facts[key] = value
        return facts

    def _extract_location(self, lines: list[str], headings: list[str]) -> tuple[str | None, str | None]:
        location = self._section_text(lines, headings)
        if not location:
            return None, None
        location_lines = [line.strip() for line in location.splitlines() if line.strip()]
        if not location_lines:
            return None, None
        name = location_lines[0]
        address = ", ".join(location_lines[1:]) if len(location_lines) > 1 else None
        return name, address

    def _looks_like_section_heading(self, line: str) -> bool:
        normalized = line.lower().strip(":")
        known = {
            "audition date",
            "location",
            "audition location",
            "preparation",
            "personnel",
            "other dates",
            "other",
            "breakdown",
            "roles",
            "seeking",
            "submission instructions",
            "contact",
        }
        return normalized in known or bool(ROLE_HEADING_PATTERN.match(line) or ROLE_COLON_PATTERN.match(line))

    def _description(self, lines: list[str]) -> str | None:
        for label in ["description", "role description", "character description", "synopsis"]:
            value = self._field(lines, [label])
            if value:
                return value
        long_lines = [line for line in lines if len(line.split()) >= 8]
        return " ".join(long_lines[:3])[:1500] or None

    def _role_blocks(self, lines: list[str]) -> list[dict[str, Any]]:
        roles: list[dict[str, Any]] = []
        index = 0
        while index < len(lines):
            match = ROLE_HEADING_PATTERN.match(lines[index])
            colon_match = ROLE_COLON_PATTERN.match(lines[index])
            if not match:
                if not colon_match:
                    index += 1
                    continue

            block: list[str] = []
            cursor = index + 1
            if colon_match and colon_match.group("requirements"):
                block.append(colon_match.group("requirements") or "")
            while cursor < len(lines) and not ROLE_HEADING_PATTERN.match(lines[cursor]) and not ROLE_COLON_PATTERN.match(lines[cursor]):
                block.append(lines[cursor])
                cursor += 1

            role_name = match.group("name") if match else colon_match.group("name")
            role_type = match.group("type") if match else None
            parsed = self._parse_role_block(role_name, role_type, block)
            if parsed:
                roles.append(parsed)
            index = cursor
        return roles

    def _parse_role_block(self, role_name: str, role_type: str | None, block: list[str]) -> dict[str, Any] | None:
        if not block:
            return None
        block_text = " ".join(block)
        if not any(keyword in block_text.lower() for keyword in REQUIREMENT_KEYWORDS) and not re.search(r"\[[^\]]+\]|\d{2}\s*(?:-|–|to)\s*\d{2}", block_text):
            return None

        requirement_line = self._requirement_line(block)
        if not requirement_line and "|" in block[0]:
            requirement_line = block[0]
        description_lines = [
            line
            for line in block
            if line != requirement_line and len(line.split()) >= 8 and not self._looks_like_requirement(line)
        ]
        character_description = " ".join(description_lines[:3])[:1500] or None
        return self._clean_dict(
            {
                "role_name": role_name.strip(),
                "role_type": role_type.strip().title() if role_type else self._extract_billing(block_text),
                "billing": self._extract_billing(block_text),
                "character_description": character_description,
                "gender_presentation": self._extract_gender(requirement_line or block_text),
                "ethnicity": self._extract_ethnicity(requirement_line or block_text),
                "age_range": self._extract_role_age(requirement_line or block_text),
                "height_requirement": self._extract_height_requirement(block_text),
                "vocal_requirements": self._extract_vocal_requirements(block),
                "dance_requirements": self._extract_dance_requirements(block),
                "movement_requirements": self._extract_movement_requirements(block),
                "special_skills": self._extract_special_skills(block_text),
                "skills_required": self._extract_role_skills(block),
                "language_requirements": self._extract_languages(block_text),
                "archetypes": self._extract_archetypes(block_text),
                "preparation_notes": self._extract_preparation_notes(block),
                "confidence_score": self._role_confidence(requirement_line, character_description, block_text),
                "extracted_facts": self._role_extracted_facts(
                    role_name=role_name.strip(),
                    role_type=role_type.strip().title() if role_type else self._extract_billing(block_text),
                    billing=self._extract_billing(block_text),
                    character_description=character_description,
                    requirement_text=requirement_line or block_text,
                    block_text=block_text,
                ),
                "ai_inference": self._role_ai_inference(block_text),
                "role_requirement_text": block_text[:3000],
            }
        )

    def _requirement_line(self, block: list[str]) -> str | None:
        for line in block:
            lower = line.lower()
            if any(term.lower() in lower for term in GENDER_TERMS) and (
                "should read" in lower or "," in line or "seeking" in lower
            ):
                return line
        return None

    def _looks_like_requirement(self, line: str) -> bool:
        return any(keyword in line.lower() for keyword in REQUIREMENT_KEYWORDS)

    def _extract_gender(self, text: str) -> str | None:
        match = re.search(r"\b(Female|Male|Woman|Man)\s+Presenting\b", text, flags=re.I)
        if match:
            return f"{match.group(1).title()} Presenting"
        for term in GENDER_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", text, flags=re.I):
                return term.replace("Non-binary", "Nonbinary")
        return None

    def _extract_ethnicity(self, text: str) -> str | None:
        bracket_parts = [part.strip(" []") for part in re.split(r"\|", text) if part.strip(" []")]
        for part in bracket_parts:
            if not re.search(r"\b(?:female|male|woman|man|presenting|\d{2}\s*(?:-|–|to)\s*\d{2})\b", part, flags=re.I):
                return part
        match = re.search(
            r"\b(?:Female|Male|Woman|Man|Nonbinary|Non-binary|Trans)\s*,\s*([^,;]+)",
            text,
            flags=re.I,
        )
        return match.group(1).strip() if match else None

    def _extract_role_age(self, text: str) -> str | None:
        patterns = [
            r"\b(\d{2}\s*(?:-|–|to)\s*\d{2})\b",
            r"should\s+read\s+(?:age\s+)?((?:late|early|mid)\s+teens)",
            r"should\s+read\s+(?:age\s+)?((?:late|early|mid)\s+\d{2}s)",
            r"should\s+read\s+(?:age\s+)?(\d{2})",
            r"\b(?:ages?|age range|playable age)\s*:?\s*(\d{2}\s*(?:-|–|to)\s*\d{2})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return match.group(1).strip()
        return None

    def _extract_height_requirement(self, text: str) -> str | None:
        match = re.search(r"\b\d\s*[’']\s*\d{1,2}\s*[\"”]?\s*(?:and\s+)?(?:under|over|or\s+shorter|or\s+taller)\b", text, flags=re.I)
        return match.group(0).strip() if match else None

    def _extract_vocal_requirements(self, block: list[str]) -> str | None:
        vocal_lines = [
            line
            for line in block
            if re.search(r"\b(vocalist|singer|sing|tenor|baritone|soprano|alto|belt|mix|brassy|legit|musical theatre|musical theater|latin-pop|jazz)\b", line, flags=re.I)
        ]
        return " ".join(vocal_lines)[:1200] or None

    def _extract_role_skills(self, block: list[str]) -> str | None:
        skill_lines = [
            line
            for line in block
            if re.search(r"\b(movement|dance|martial arts|stage combat|athletic|jiu-jitsu|judo|grappling|mma|guitar)\b", line, flags=re.I)
        ]
        return " ".join(skill_lines)[:1200] or None

    def _extract_dance_requirements(self, block: list[str]) -> str | None:
        dance_lines = [line for line in block if re.search(r"\b(dance|dancer)\b", line, flags=re.I)]
        return " ".join(dance_lines)[:1200] or None

    def _extract_movement_requirements(self, block: list[str]) -> str | None:
        movement_lines = [
            line
            for line in block
            if re.search(r"\b(movement|physical storytelling|martial arts|stage combat|athletic|dance)\b", line, flags=re.I)
        ]
        return " ".join(movement_lines)[:1200] or None

    def _extract_special_skills(self, text: str) -> str | None:
        skills = [
            skill
            for skill in ["Brazilian Jiu-Jitsu", "judo", "grappling", "MMA", "stage combat", "guitar", "comedy", "musical theater"]
            if re.search(rf"\b{re.escape(skill)}\b", text, flags=re.I)
        ]
        return ", ".join(dict.fromkeys(skills)) or None

    def _extract_billing(self, text: str) -> str | None:
        match = re.search(r"\b(lead|principal|supporting|featured|ensemble|chorus|understudy|swing)\b", text, flags=re.I)
        return match.group(1).title() if match else None

    def _extract_archetypes(self, text: str) -> list[str]:
        archetypes: list[str] = []
        patterns = {
            "Comedy": r"\b(comedic|comedy|funny)\b",
            "Scene Stealer": r"\b(scene[- ]?stealer|bold personality)\b",
            "Warm Energy": r"\b(warm|lovable|heart|generous)\b",
            "Musical Theater": r"\b(musical theatre|musical theater|belt|legit musical)\b",
        }
        for label, pattern in patterns.items():
            if re.search(pattern, text, flags=re.I):
                archetypes.append(label)
        return archetypes

    def _breakdown_extracted_facts(
        self,
        *,
        production_details: dict[str, Any],
        role_details: dict[str, Any],
        submission_instructions: str | None,
        date_facts: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._clean_dict(
            {
                "dates": date_facts or {},
                "production_details": production_details,
                "audition_information": self._clean_dict(
                    {
                        "audition_type": role_details.get("audition_type"),
                        "audition_subtype": role_details.get("audition_subtype"),
                        "audition_date": role_details.get("audition_date"),
                        "audition_time": role_details.get("audition_time"),
                        "audition_location_name": role_details.get("audition_location_name"),
                        "audition_address": role_details.get("audition_address"),
                    }
                ),
                "preparation": role_details.get("preparation"),
                "submission_instructions": submission_instructions,
                "roles": [role.get("extracted_facts", {}) for role in role_details.get("available_roles", [])],
            }
        )

    def _breakdown_ai_inference(
        self,
        *,
        classification: str,
        role_details: dict[str, Any],
        production_details: dict[str, Any],
    ) -> dict[str, Any]:
        return self._clean_dict(
            {
                "breakdown_classification": {
                    "value": classification,
                    "confidence": 70,
                    "explanation": "Inferred from acting-role signals in the breakdown text.",
                },
                "project_type": {
                    "value": production_details.get("project_type"),
                    "confidence": 75 if production_details.get("project_type") else 40,
                    "explanation": "Inferred from production and audition language.",
                },
                "role_archetypes": [
                    {
                        "role_name": role.get("role_name"),
                        "value": role.get("archetypes", []),
                        "confidence": role.get("confidence_score", 50),
                        "explanation": "Inferred from role description.",
                    }
                    for role in role_details.get("available_roles", [])
                    if role.get("archetypes")
                ],
            }
        )

    def _role_extracted_facts(
        self,
        *,
        role_name: str,
        role_type: str | None,
        billing: str | None,
        character_description: str | None,
        requirement_text: str,
        block_text: str,
    ) -> dict[str, Any]:
        return self._clean_dict(
            {
                "role_name": role_name,
                "role_type": role_type,
                "billing": billing,
                "character_description": character_description,
                "gender_presentation": self._extract_gender(requirement_text),
                "ethnicity_or_cultural_background": self._extract_ethnicity(requirement_text),
                "age_range": self._extract_role_age(requirement_text),
                "height_requirements": self._extract_height_requirement(block_text),
                "vocal_requirements": self._extract_vocal_requirements([block_text]),
                "dance_requirements": self._extract_dance_requirements([block_text]),
                "movement_requirements": self._extract_movement_requirements([block_text]),
                "language_requirements": self._extract_languages(block_text),
                "special_skills": self._extract_special_skills(block_text),
                "preparation_notes": self._extract_preparation_notes([block_text]),
            }
        )

    def _role_ai_inference(self, text: str) -> dict[str, Any]:
        archetypes = self._extract_archetypes(text)
        return self._clean_dict(
            {
                "likely_archetypes": {
                    "value": archetypes,
                    "confidence": 70 if archetypes else 35,
                    "explanation": "Inferred from role description.",
                },
                "likely_tone": {
                    "value": "Comedy" if re.search(r"\b(comedic|comedy|funny|scene[- ]?stealer)\b", text, flags=re.I) else None,
                    "confidence": 70,
                    "explanation": "Inferred from role description.",
                },
            }
        )

    def _extract_preparation_notes(self, block: list[str]) -> str | None:
        notes = [line for line in block if re.search(r"\b(prepare|song|selection|sides|monologue|bring)\b", line, flags=re.I)]
        return " ".join(notes)[:1200] or None

    def _role_confidence(self, requirement_line: str | None, character_description: str | None, text: str) -> int:
        score = 40
        if requirement_line:
            score += 25
        if character_description:
            score += 15
        if re.search(r"\b\d{2}\s*(?:-|–|to)\s*\d{2}\b", text):
            score += 10
        if re.search(r"\b(female|male|woman|man|black|latine|asian|white)\b", text, flags=re.I):
            score += 10
        return min(100, score)

    def _extract_languages(self, text: str) -> str | None:
        found = [
            language
            for language in ["Portuguese", "Spanish", "Cuban Spanish", "Brazilian Portuguese"]
            if re.search(rf"\b{re.escape(language)}\b", text, flags=re.I)
        ]
        return ", ".join(dict.fromkeys(found)) or None

    def _actor_facing_description(self, text: str, role: str) -> str | None:
        if not text:
            return None
        generic_prefix = "public playbill breakdown discovered from the jobs page:"
        lowered = text.lower()
        if lowered.startswith(generic_prefix):
            return role
        return self._description([text])

    def _summary(self, production: dict, role: dict, submission_instructions: str | None) -> str:
        parts = []
        role_name = role.get("role_name") or "Role"
        project_type = production.get("project_type")
        union = production.get("union_status")
        is_theater = project_type and any(term in str(project_type).lower() for term in ["theatre", "theater"])
        location = production.get("performance_location") or production.get("audition_location_name") if is_theater else production.get("shoot_location")
        audition_type = role.get("audition_type")
        due = role.get("self_tape_due_date")
        parts.append(f"{role_name}")
        if project_type:
            parts.append(f"in a {project_type.lower()} project")
        if union:
            parts.append(f"({union})")
        if location:
            parts.append(f"{'at' if is_theater else 'shooting in'} {location}")
        if audition_type:
            parts.append(f"with a {audition_type.lower()} audition")
        if due:
            parts.append(f"due {due}")
        if submission_instructions:
            parts.append("submission instructions are available")
        return " ".join(parts).strip() + "."

    def _yes_no(self, value: bool | None) -> str | None:
        if value is None:
            return None
        return "Yes" if value else "No"

    def _clean_text(self, text: str) -> str:
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _clean_dict(self, data: dict) -> dict:
        return {key: value for key, value in data.items() if value not in [None, "", [], {}]}
