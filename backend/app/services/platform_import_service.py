from __future__ import annotations

import csv
import html
import re
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import (
    ActingCredit,
    ActorProfile,
    Asset,
    PlatformAssetMapping,
    PlatformProfile,
    PublicProfileImport,
)
from app.schemas.platform import (
    PlatformAssetMappingCreate,
    PlatformAssetMappingUpdate,
    PlatformProfileImportCreate,
    PlatformProfileUpdate,
    PublicProfileImportCreate,
    PublicProfileImportUpdate,
)
from app.services.file_storage_service import FileStorageService
from app.services.skill_parser_service import SkillParserService


ASSET_TYPES = {
    "headshot": "Headshot",
    "photo": "Headshot",
    "reel": "Reel",
    "clip": "Reel",
    "slate": "Slate",
    "resume": "Resume",
}

RESUME_SECTION_CATEGORIES = {
    "television": "Television",
    "tv": "Television",
    "film": "Film",
    "film/ new media": "New Media",
    "film/new media": "New Media",
    "new media": "New Media",
    "commercial": "Commercial",
    "commercials": "Commercial",
    "theater": "Theater",
    "theatre": "Theater",
    "voiceover": "Voiceover",
    "industrial": "Industrial",
    "print": "Print",
    "training": "Training",
    "education": "Training",
    "special skills": "Special Skills",
    "skills": "Special Skills",
}

ROLE_TYPES = [
    "Series Regular",
    "Guest Star",
    "Co-Star",
    "Recurring",
    "Supporting",
    "Lead/Voice",
    "Lead",
    "Principal",
    "Featured",
    "Host",
    "Myself/Lead",
    "Myself",
]

BLOCKED_HINTS = {
    "login",
    "sign in",
    "access denied",
    "forbidden",
    "captcha",
    "verify you are human",
    "enable javascript",
    "not authorized",
}

CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class PlatformImportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_profiles(self) -> list[PlatformProfile]:
        return list(self.db.scalars(select(PlatformProfile).order_by(PlatformProfile.imported_at.desc())))

    def list_public_imports(self) -> list[PublicProfileImport]:
        return list(
            self.db.scalars(
                select(PublicProfileImport).order_by(PublicProfileImport.imported_at.desc())
            )
        )

    def import_public_profile_url(self, payload: PublicProfileImportCreate) -> PublicProfileImport:
        visible_text = ""
        error_message = None
        status = "Draft"
        parsed: dict = {}
        try:
            visible_text = self._fetch_public_visible_text(payload.profile_url)
            if self._looks_blocked(visible_text):
                status = "Blocked"
                error_message = (
                    "The public/shareable page appears to block automated fetching or requires login. "
                    "No bypass was attempted. Use copy/paste, PDF upload, screenshot upload, CSV, or guided manual import instead."
                )
            else:
                parsed = self._parse_public_profile(visible_text, payload.profile_url)
                status = "Draft" if parsed.get("confidence") != "Low" else "Needs Review"
        except ValueError as exc:
            status = "Blocked"
            error_message = str(exc)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            status = "Blocked"
            error_message = (
                f"Could not fetch visible public page content: {exc}. No bypass was attempted. "
                "Use copy/paste, PDF upload, screenshot upload, CSV, or guided manual import instead."
            )
        record = PublicProfileImport(
            platform_name=payload.platform_name,
            profile_url=payload.profile_url,
            import_method="Public/shareable profile URL",
            imported_at=datetime.now(timezone.utc),
            raw_visible_text=visible_text,
            parsed_data_json=parsed,
            import_status=status,
            user_approved=False,
            error_message=error_message,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def update_public_import(
        self, import_id: UUID, payload: PublicProfileImportUpdate
    ) -> PublicProfileImport:
        record = self._public_import_or_404(import_id)
        data = payload.model_dump(exclude_unset=True)
        if "raw_visible_text" in data and data["raw_visible_text"]:
            record.parsed_data_json = self._parse_public_profile(data["raw_visible_text"], record.profile_url)
            record.import_status = "Draft"
            record.error_message = None
        for key, value in data.items():
            setattr(record, key, value)
        self.db.commit()
        self.db.refresh(record)
        return record

    def approve_public_import(
        self, import_id: UUID
    ) -> tuple[PublicProfileImport, list[PlatformAssetMapping]]:
        record = self._public_import_or_404(import_id)
        if record.import_status == "Blocked":
            raise ValueError("Blocked imports cannot be approved. Use a manual import method instead.")
        created = self._create_mappings_from_parsed(
            record.platform_name,
            record.parsed_data_json.get("platform_assets", []),
            "Draft-imported from visible public/shareable profile data provided by URL.",
        )
        record.import_status = "Approved"
        record.user_approved = True
        self.db.commit()
        self.db.refresh(record)
        for mapping in created:
            self.db.refresh(mapping)
        return record, created

    def reject_public_import(self, import_id: UUID) -> PublicProfileImport:
        record = self._public_import_or_404(import_id)
        record.import_status = "Rejected"
        record.user_approved = False
        self.db.commit()
        self.db.refresh(record)
        return record

    def delete_public_import(self, import_id: UUID) -> None:
        record = self._public_import_or_404(import_id)
        self.db.delete(record)
        self.db.commit()

    def import_from_text(self, payload: PlatformProfileImportCreate) -> PlatformProfile:
        self._validate_actor(payload.actor_profile_id)
        raw_import_text = self._clean_import_text(payload.raw_import_text)
        parsed = self._parse_profile(raw_import_text, payload.import_method)
        profile = PlatformProfile(
            actor_profile_id=payload.actor_profile_id,
            platform_name=payload.platform_name,
            profile_url=payload.profile_url,
            imported_at=datetime.now(timezone.utc),
            import_method=payload.import_method,
            raw_import_text=raw_import_text,
            import_status="Draft" if parsed["confidence"] != "Low" else "Needs Review",
            user_approved=False,
            parsed_profile=parsed,
        )
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def import_from_upload(
        self,
        actor_profile_id: UUID | None,
        platform_name: str,
        profile_url: str | None,
        import_method: str,
        upload: UploadFile | None,
        raw_import_text: str | None = None,
    ) -> PlatformProfile:
        text_parts: list[str] = []
        if upload is not None:
            path, _size = FileStorageService().save_upload(upload)
            filename = upload.filename or Path(path).name
            upload_text = self._extract_upload_text(path, filename, upload.content_type or "")
            if upload_text.strip():
                text_parts.append(f"Uploaded file: {filename}\n\n{upload_text.strip()}")
            else:
                text_parts.append(
                    f"Uploaded file: {filename}. "
                    "No reliable text could be extracted locally from this file."
                )
        if raw_import_text and raw_import_text.strip():
            text_parts.append(f"User-provided profile text:\n\n{raw_import_text.strip()}")
        if not text_parts:
            raise ValueError("Add an uploaded file, pasted profile text, or both before creating a draft import.")
        raw_text = "\n\n---\n\n".join(text_parts)
        return self.import_from_text(
            PlatformProfileImportCreate(
                actor_profile_id=actor_profile_id,
                platform_name=platform_name,
                profile_url=profile_url,
                import_method=import_method,
                raw_import_text=raw_text,
            )
        )

    def update_profile(self, profile_id: UUID, payload: PlatformProfileUpdate) -> PlatformProfile:
        profile = self._profile_or_404(profile_id)
        data = payload.model_dump(exclude_unset=True)
        if "raw_import_text" in data and data["raw_import_text"]:
            data["raw_import_text"] = self._clean_import_text(data["raw_import_text"])
            profile.parsed_profile = self._parse_profile(data["raw_import_text"], profile.import_method)
        for key, value in data.items():
            setattr(profile, key, value)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def approve_profile(self, profile_id: UUID) -> tuple[PlatformProfile, list[PlatformAssetMapping]]:
        profile = self._profile_or_404(profile_id)
        created = self._create_mappings_from_parsed(
            profile.platform_name,
            profile.parsed_profile.get("platform_assets", []),
            "Draft-imported from user-provided platform profile data.",
        )
        if profile.actor_profile_id:
            self._create_credits_from_parsed(profile.actor_profile_id, profile.parsed_profile)
            self._apply_skills_to_actor(profile.actor_profile_id, profile.parsed_profile)
        profile.import_status = "Approved"
        profile.user_approved = True
        self.db.commit()
        self.db.refresh(profile)
        for mapping in created:
            self.db.refresh(mapping)
        return profile, created

    def reject_profile(self, profile_id: UUID) -> PlatformProfile:
        profile = self._profile_or_404(profile_id)
        profile.import_status = "Rejected"
        profile.user_approved = False
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_profile(self, profile_id: UUID) -> None:
        profile = self._profile_or_404(profile_id)
        self.db.delete(profile)
        self.db.commit()

    def list_mappings(self) -> list[PlatformAssetMapping]:
        return list(self.db.scalars(select(PlatformAssetMapping).order_by(PlatformAssetMapping.updated_at.desc())))

    def create_mapping(self, payload: PlatformAssetMappingCreate) -> PlatformAssetMapping:
        self._validate_asset(payload.local_asset_id)
        mapping = PlatformAssetMapping(**payload.model_dump())
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def update_mapping(self, mapping_id: UUID, payload: PlatformAssetMappingUpdate) -> PlatformAssetMapping:
        mapping = self._mapping_or_404(mapping_id)
        data = payload.model_dump(exclude_unset=True)
        self._validate_asset(data.get("local_asset_id"))
        for key, value in data.items():
            setattr(mapping, key, value)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def delete_mapping(self, mapping_id: UUID) -> None:
        mapping = self._mapping_or_404(mapping_id)
        self.db.delete(mapping)
        self.db.commit()

    def _parse_profile(self, text: str, import_method: str) -> dict:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        joined = "\n".join(lines)
        lowered = joined.lower()
        skills = self._extract_skills(lines)
        parsed_skills = SkillParserService().parse_items(skills)
        structured_credits = self._extract_structured_credits(lines)
        credits = [
            {"section": credit["category"], "credit": credit["raw_credit"]}
            for credit in structured_credits
            if credit.get("raw_credit")
        ]
        resume_sections = self._extract_resume_sections(lines)
        platform_assets = self._extract_assets(lines)
        playable = self._extract_playable_age(joined)
        union = self._extract_union(joined)
        profile_name = self._extract_name(lines)
        if import_method == "Uploaded CSV":
            csv_data = self._parse_csv(joined)
            platform_assets.extend(csv_data["platform_assets"])
            skills.extend(csv_data["skills"])
            parsed_skills = SkillParserService().parse_items(skills)
        confidence = "High" if profile_name and (skills or credits or platform_assets) else "Medium"
        if "no reliable text could be extracted" in lowered:
            confidence = "Low"
        return {
            "profile_name": profile_name,
            "playable_age_range": playable,
            "union_status": union,
            "skills": sorted(set(SkillParserService().actor_skills(parsed_skills))),
            "accents": sorted(set(SkillParserService().accents(parsed_skills))),
            "skill_categories": SkillParserService().grouped(parsed_skills),
            "structured_skills": [
                {"skill_name": skill.name, "skill_category": skill.category, "proficiency": skill.proficiency}
                for skill in parsed_skills
            ],
            "credits": credits,
            "structured_credits": structured_credits,
            "resume_sections": resume_sections,
            "headshot_names": [item["name"] for item in platform_assets if item["asset_type"] == "Headshot"],
            "reel_names": [item["name"] for item in platform_assets if item["asset_type"] == "Reel"],
            "slate_names": [item["name"] for item in platform_assets if item["asset_type"] == "Slate"],
            "media_descriptions": [item["description"] for item in platform_assets if item.get("description")],
            "platform_assets": platform_assets,
            "confidence": confidence,
            "compliance_note": "Parsed only from user-provided data. No logged-in pages were scraped and no protected media was downloaded.",
        }

    def _parse_public_profile(self, text: str, url: str) -> dict:
        parsed = self._parse_profile(text, "Public/shareable profile URL")
        parsed["source_url"] = url
        parsed["draft_records"] = {
            "actor_profile": {
                "name": parsed.get("profile_name"),
                "playable_age_range": parsed.get("playable_age_range"),
                "union_status": parsed.get("union_status"),
                "skills": parsed.get("skills", []),
            },
            "credits": parsed.get("credits", []),
            "skills": parsed.get("skills", []),
            "resume_sections": parsed.get("resume_sections", {}),
            "platform_asset_mappings": parsed.get("platform_assets", []),
        }
        parsed["compliance_note"] = (
            "Parsed from visible public/shareable page text only. No login, authentication bypass, "
            "protected media download, hidden account scraping, background crawling, or multi-profile scraping was performed."
        )
        return parsed

    def _extract_upload_text(self, path: str, filename: str, content_type: str) -> str:
        suffix = Path(filename).suffix.lower()
        data = Path(path).read_bytes()
        if suffix == ".csv" or "csv" in content_type:
            return self._clean_import_text(data.decode("utf-8", errors="ignore"))
        if suffix in {".txt", ".md"} or "text" in content_type:
            return self._clean_import_text(data.decode("utf-8", errors="ignore"))
        if suffix == ".pdf" or "pdf" in content_type:
            return self._clean_import_text(self._extract_pdf_text(path, data))
        if suffix in {".png", ".jpg", ".jpeg", ".webp"} or "image" in content_type:
            return ""
        return self._clean_import_text(data.decode("utf-8", errors="ignore"))

    def _extract_pdf_text(self, path: str, data: bytes) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            decoded = data.decode("latin-1", errors="ignore")
            snippets = re.findall(r"\(([^()]{2,120})\)", decoded)
            return "\n".join(snippets[:400])

    def _clean_import_text(self, text: str) -> str:
        cleaned = CONTROL_CHAR_PATTERN.sub(" ", text.replace("\x00", " "))
        cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in cleaned.splitlines())
        return cleaned.strip()

    def _fetch_public_visible_text(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Enter a valid public or shareable http(s) profile URL.")
        request = Request(
            url,
            headers={
                "User-Agent": "CastingIntelligenceAgent/1.0 (+user-triggered public profile portability import)",
                "Accept": "text/html,text/plain;q=0.9,*/*;q=0.5",
            },
            method="GET",
        )
        with urlopen(request, timeout=10) as response:
            content_type = response.headers.get("content-type", "")
            if "text" not in content_type and "html" not in content_type and "json" not in content_type:
                raise ValueError(
                    "The URL did not return visible text/html content. No protected media was downloaded."
                )
            raw = response.read(1_000_000)
        return self._html_to_visible_text(raw.decode("utf-8", errors="ignore"))

    def _html_to_visible_text(self, content: str) -> str:
        content = re.sub(r"(?is)<(script|style|noscript|svg|canvas).*?>.*?</\1>", " ", content)
        content = re.sub(r"(?is)<!--.*?-->", " ", content)
        content = re.sub(r"(?i)<br\s*/?>", "\n", content)
        content = re.sub(r"(?i)</(p|div|li|h[1-6]|section|article|tr)>", "\n", content)
        content = re.sub(r"(?is)<[^>]+>", " ", content)
        content = html.unescape(content)
        lines = [re.sub(r"\s+", " ", line).strip() for line in content.splitlines()]
        return "\n".join(line for line in lines if line)

    def _looks_blocked(self, visible_text: str) -> bool:
        lowered = visible_text.lower()
        if len(visible_text.strip()) < 80:
            return True
        return any(hint in lowered for hint in BLOCKED_HINTS)

    def _extract_name(self, lines: list[str]) -> str | None:
        for line in lines[:8]:
            lowered = line.lower()
            if self._is_noise_line(line) or lowered in RESUME_SECTION_CATEGORIES:
                continue
            if " - sag-aftra" in lowered:
                return re.split(r"\s+-\s+sag-aftra", line, flags=re.I)[0].strip()
            if ":" in line:
                label, value = line.split(":", 1)
                if label.strip().lower() in {"name", "actor", "profile name"} and value.strip():
                    return value.strip()
            if 2 <= len(line.split()) <= 4 and not any(char.isdigit() for char in line):
                return line
        return None

    def _extract_playable_age(self, text: str) -> dict | None:
        match = re.search(r"(playable age|age range|plays)\D{0,20}(\d{2})\D{1,5}(\d{2})", text, re.I)
        if not match:
            return None
        return {"min": int(match.group(2)), "max": int(match.group(3))}

    def _extract_union(self, text: str) -> str | None:
        for value in ["SAG-AFTRA", "SAG Eligible", "Non-Union", "AEA", "ACTRA"]:
            if value.lower() in text.lower():
                return value
        return None

    def _extract_list_after_label(self, lines: list[str], labels: list[str]) -> list[str]:
        items = []
        for line in lines:
            if ":" not in line:
                continue
            label, value = line.split(":", 1)
            if label.strip().lower() in labels:
                items.extend(self._split_items(value))
        return items

    def _extract_skills(self, lines: list[str]) -> list[str]:
        skills = self._extract_list_after_label(lines, ["skills", "special skills"])
        active = False
        for line in lines:
            normalized = line.strip().lower().rstrip(":")
            if normalized in {"physical characteristics / measurements", "physical characteristics", "measurements"}:
                active = True
                continue
            if normalized in RESUME_SECTION_CATEGORIES and normalized not in {"skills", "special skills"}:
                active = False
            if not active or ":" in line and not "," in line:
                continue
            skills.extend(self._split_items(line))
        return [skill for skill in skills if not skill.lower().startswith(("height:", "weight:"))]

    def _extract_structured_credits(self, lines: list[str]) -> list[dict]:
        credits = []
        active_category = None
        display_order_by_category: dict[str, int] = {}
        for line in lines:
            if self._is_noise_line(line):
                continue
            section = self._resume_category(line)
            if section:
                active_category = section
                display_order_by_category.setdefault(section, 0)
                continue
            if not active_category or len(line.split()) < 2:
                continue
            if active_category == "Special Skills":
                continue
            order = display_order_by_category.get(active_category, 0)
            display_order_by_category[active_category] = order + 1
            credits.append(self._parse_credit_line(line, active_category, order))
        return credits[:120]

    def _parse_credit_line(self, line: str, category: str, display_order: int) -> dict:
        base = {
            "category": category,
            "display_order": display_order,
            "raw_credit": line,
        }
        if category == "Training":
            parts = self._split_credit_columns(line)
            parsed_training = self._parse_training_line(line)
            base.update(
                {
                    "class_or_program": parsed_training.get("class_or_program") or (parts[0] if parts else line),
                    "instructor": parsed_training.get("instructor") or (parts[1] if len(parts) > 1 else None),
                    "institution": parsed_training.get("institution") or (parts[2] if len(parts) > 2 else None),
                    "year": parsed_training.get("year"),
                }
            )
            return base

        if category == "Theater":
            parsed_theater = self._parse_theater_line(line)
            if parsed_theater:
                base.update(parsed_theater)
                return base

        role_match = self._find_role_type(line)
        if role_match:
            project = line[: role_match.start()].strip()
            remainder = line[role_match.end() :].strip()
            base.update(
                {
                    "project_title": project or line,
                    "role_or_character": role_match.group(0),
                    "role_type": role_match.group(0),
                    "production_company": remainder or None,
                    "director": self._extract_director(remainder),
                }
            )
            return base

        parts = self._split_credit_columns(line)
        base.update(
            {
                "project_title": parts[0] if parts else line,
                "role_or_character": parts[1] if len(parts) > 1 else None,
                "production_company": parts[2] if len(parts) > 2 else None,
                "director": self._extract_director(line),
            }
        )
        return base

    def _parse_theater_line(self, line: str) -> dict | None:
        parts = self._split_credit_columns(line)
        if len(parts) >= 3:
            return {
                "project_title": parts[0],
                "role_or_character": parts[1],
                "production_company": parts[2],
                "director": self._extract_director(parts[3] if len(parts) > 3 else line),
            }
        director = self._extract_director(line)
        cleaned = re.sub(r"\bDir\.\s*.+$", "", line).strip()
        known_roles = (
            "Stage Directions",
            "Beggar/Judge",
            "Ella (old and young)",
            "Foufoune",
            "Fufune",
            "Madame",
            "Tatiana",
            "Feste",
            "Rosie",
            "Sharee",
            "Bina",
            "Andy",
        )
        for role in sorted(known_roles, key=len, reverse=True):
            pattern = rf"^(?P<project>.+?)\s+(?P<role>{re.escape(role)})(?:\s+(?P<venue>.+))?$"
            match = re.match(pattern, cleaned, flags=re.I)
            if match:
                return {
                    "project_title": match.group("project").strip(),
                    "role_or_character": match.group("role").strip(),
                    "production_company": (match.group("venue") or "").strip() or None,
                    "director": director,
                }
        return None

    def _parse_training_line(self, line: str) -> dict:
        parts = self._split_credit_columns(line)
        if len(parts) >= 2:
            return {
                "class_or_program": parts[0],
                "instructor": parts[1],
                "institution": parts[2] if len(parts) > 2 else None,
            }
        match = re.match(r"^(?P<class>.+?)\s+(?P<instructor>[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+){1,3}(?:,\s*CD)?)$", line)
        if match:
            return {
                "class_or_program": match.group("class").strip(),
                "instructor": match.group("instructor").strip(),
            }
        degree = re.match(r"^(?P<class>AA|A\\.A\\.|BA|BFA|MFA|MA).+?(?P<institution>Niagara.+?College)(?:,?\s*(?P<year>\\d{4}))?$", line, flags=re.I)
        if degree:
            return {
                "class_or_program": line[: degree.start("institution")].strip(" ,-"),
                "institution": degree.group("institution").strip(),
                "year": degree.group("year"),
            }
        return {}

    def _split_credit_columns(self, line: str) -> list[str]:
        parts = [part.strip() for part in re.split(r"\s{2,}|\t+", line) if part.strip()]
        if len(parts) > 1:
            return parts
        return [line.strip()]

    def _find_role_type(self, line: str) -> re.Match[str] | None:
        pattern = r"\b(" + "|".join(re.escape(role) for role in ROLE_TYPES) + r")\b"
        return re.search(pattern, line, re.I)

    def _extract_director(self, text: str | None) -> str | None:
        if not text:
            return None
        match = re.search(r"\bDir\.\s*(.+)$", text)
        return match.group(1).strip() if match else None

    def _resume_category(self, line: str) -> str | None:
        return RESUME_SECTION_CATEGORIES.get(line.strip().lower().rstrip(":"))

    def _is_noise_line(self, line: str) -> bool:
        lowered = line.strip().lower()
        return (
            not lowered
            or lowered.startswith("www.")
            or lowered in {"breakdown services, ltd.", "résumé", "resume"}
            or "play slateshot" in lowered
            or lowered.startswith("represented by")
            or re.fullmatch(r"[\W_]+", lowered) is not None
        )

    def _extract_section_items(self, lines: list[str], headers: list[str]) -> list[dict]:
        credits = []
        active = None
        for line in lines:
            normalized = line.strip().lower().rstrip(":")
            if normalized in headers:
                active = line.strip().rstrip(":")
                continue
            if active and len(line.split()) >= 2:
                credits.append({"section": active, "credit": line})
        return credits[:80]

    def _extract_resume_sections(self, lines: list[str]) -> dict:
        sections: dict[str, list[str]] = {}
        active = None
        for line in lines:
            category = self._resume_category(line)
            if category:
                active = category
                sections.setdefault(active, [])
                continue
            if active and not self._is_noise_line(line):
                sections[active].append(line)
        return sections

    def _extract_assets(self, lines: list[str]) -> list[dict]:
        assets = []
        for line in lines:
            lower = line.lower()
            asset_type = next((value for key, value in ASSET_TYPES.items() if key in lower), None)
            if not asset_type:
                continue
            name = line.split(":", 1)[1].strip() if ":" in line else line.strip()
            assets.append(
                {
                    "name": name[:255],
                    "asset_type": asset_type,
                    "tags": [],
                    "archetypes": [],
                    "description": line,
                }
            )
        return assets[:80]

    def _parse_csv(self, text: str) -> dict:
        result = {"platform_assets": [], "skills": []}
        try:
            reader = csv.DictReader(StringIO(text))
            for row in reader:
                row_text = " ".join(str(value) for value in row.values() if value)
                asset_type = next((value for key, value in ASSET_TYPES.items() if key in row_text.lower()), None)
                if asset_type:
                    name = row.get("name") or row.get("asset_name") or row.get("title") or row_text
                    result["platform_assets"].append({"name": name[:255], "asset_type": asset_type, "tags": [], "archetypes": [], "description": row_text})
                if row.get("skills"):
                    result["skills"].extend(self._split_items(row["skills"]))
        except csv.Error:
            return result
        return result

    def _split_items(self, value: str) -> list[str]:
        return [item.strip() for item in re.split(r"[,;|]", value) if item.strip()]

    def _validate_actor(self, actor_profile_id: UUID | None) -> None:
        if actor_profile_id and not self.db.get(ActorProfile, actor_profile_id):
            raise NotFoundError("Actor profile not found")

    def _validate_asset(self, asset_id: UUID | None) -> None:
        if asset_id and not self.db.get(Asset, asset_id):
            raise NotFoundError("Local asset not found")

    def _profile_or_404(self, profile_id: UUID) -> PlatformProfile:
        profile = self.db.get(PlatformProfile, profile_id)
        if not profile:
            raise NotFoundError("Platform profile import not found")
        return profile

    def _mapping_or_404(self, mapping_id: UUID) -> PlatformAssetMapping:
        mapping = self.db.get(PlatformAssetMapping, mapping_id)
        if not mapping:
            raise NotFoundError("Platform asset mapping not found")
        return mapping

    def _public_import_or_404(self, import_id: UUID) -> PublicProfileImport:
        record = self.db.get(PublicProfileImport, import_id)
        if not record:
            raise NotFoundError("Public profile import not found")
        return record

    def _create_mappings_from_parsed(
        self, platform_name: str, items: list[dict], notes: str
    ) -> list[PlatformAssetMapping]:
        created = []
        for item in items:
            name = item.get("name")
            asset_type = item.get("asset_type", "Other")
            if not name:
                continue
            existing = self.db.scalars(
                select(PlatformAssetMapping).where(
                    PlatformAssetMapping.platform_name == platform_name,
                    PlatformAssetMapping.platform_asset_name == name,
                    PlatformAssetMapping.asset_type == asset_type,
                )
            ).first()
            if existing:
                continue
            mapping = PlatformAssetMapping(
                platform_name=platform_name,
                platform_asset_name=name,
                asset_type=asset_type,
                tags=item.get("tags", []),
                archetypes=item.get("archetypes", []),
                notes=notes,
            )
            self.db.add(mapping)
            created.append(mapping)
        return created

    def _create_credits_from_parsed(self, actor_profile_id: UUID, parsed_profile: dict) -> list[ActingCredit]:
        created = []
        for item in parsed_profile.get("structured_skills", []):
            skill_name = item.get("skill_name")
            if not skill_name:
                continue
            existing = self.db.scalars(
                select(ActingCredit).where(
                    ActingCredit.actor_profile_id == actor_profile_id,
                    ActingCredit.category == "Special Skills",
                    ActingCredit.skill_name == skill_name,
                )
            ).first()
            if existing:
                continue
            credit = ActingCredit(
                actor_profile_id=actor_profile_id,
                category="Special Skills",
                display_order=len(created),
                skill_name=skill_name,
                skill_category=item.get("skill_category"),
                proficiency=item.get("proficiency"),
                notes="Imported from parsed resume skills.",
            )
            self.db.add(credit)
            created.append(credit)
        for item in parsed_profile.get("structured_credits", []):
            category = item.get("category")
            if not category or category == "Special Skills":
                continue
            project_title = item.get("project_title")
            class_or_program = item.get("class_or_program")
            existing = self.db.scalars(
                select(ActingCredit).where(
                    ActingCredit.actor_profile_id == actor_profile_id,
                    ActingCredit.category == category,
                    ActingCredit.project_title == project_title,
                    ActingCredit.class_or_program == class_or_program,
                )
            ).first()
            if existing:
                continue
            credit = ActingCredit(
                actor_profile_id=actor_profile_id,
                category=category,
                display_order=item.get("display_order", 0),
                project_title=project_title,
                role_or_character=item.get("role_or_character"),
                role_type=item.get("role_type"),
                production_company=item.get("production_company"),
                director=item.get("director"),
                class_or_program=class_or_program,
                instructor=item.get("instructor"),
                institution=item.get("institution"),
                notes=f"Imported from platform profile draft. Raw row: {item.get('raw_credit')}",
            )
            self.db.add(credit)
            created.append(credit)
        return created

    def _apply_skills_to_actor(self, actor_profile_id: UUID, parsed_profile: dict) -> None:
        actor = self.db.get(ActorProfile, actor_profile_id)
        if not actor:
            return
        names = [
            item.get("skill_name")
            for item in parsed_profile.get("structured_skills", [])
            if item.get("skill_name")
        ]
        parsed = SkillParserService().parse_items(names)
        actor.skills = sorted(set([*(actor.skills or []), *SkillParserService().actor_skills(parsed)]))
        actor.accents = sorted(set([*(actor.accents or []), *SkillParserService().accents(parsed)]))
