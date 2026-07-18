from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.automation.discovery.classification import (
    ACTOR_FACING_CLASSIFICATIONS,
    REJECTED_CLASSIFICATIONS,
    classify_breakdown_text,
)
from app.db.models import ActorProfile, Opportunity


PROTECTED_PLATFORMS = {"actors access", "casting networks", "casting frontier"}


class TrustVerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def verify(self, opportunity: Opportunity, actor: ActorProfile | None = None) -> Opportunity:
        checks: list[dict] = []
        checks.append(self._demo_data_check(opportunity))
        checks.append(self._source_url_check(opportunity))
        checks.append(self._breakdown_type_check(opportunity))
        checks.append(self._role_eligibility_check(opportunity))
        checks.append(self._audition_location_check(opportunity))
        checks.extend(self._date_checks(opportunity))
        checks.append(self._platform_check(opportunity))
        checks.append(self._contact_check(opportunity))
        checks.append(self._source_category_check(opportunity))
        checks.append(self._duplicate_check(opportunity))
        checks.append(self._ai_inference_check(opportunity))
        checks.append(self._confidence_check(opportunity))
        checks.append(self._deletion_check(opportunity))

        checks = [check for check in checks if check]
        failures = [check for check in checks if check["status"] == "fail"]
        warnings = [check for check in checks if check["status"] == "warning"]
        metadata = dict(opportunity.source_metadata or {})
        metadata["trust_verification"] = {
            "status": "Blocked" if failures else "Needs Info" if warnings else "Verified",
            "failure_count": len(failures),
            "warning_count": len(warnings),
            "plain_language_reasons": [check["reason"] for check in failures + warnings],
            "checks": checks,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        opportunity.source_metadata = metadata
        return opportunity

    def _demo_data_check(self, opportunity: Opportunity) -> dict:
        if opportunity.is_demo_data:
            return self._fail("Demo Data Protection", "Demo data is hidden from real actor workflows.")
        return self._pass("Demo Data Protection", "This breakdown is not marked as demo data.")

    def _source_url_check(self, opportunity: Opportunity) -> dict:
        if not opportunity.original_post_url:
            if opportunity.source_type in {"Manual Entry", "Agent Submission", "Direct Email"}:
                return self._warn("External Link Verification", "No source link was provided. This can still be tracked as a manual breakdown.")
            return self._warn("External Link Verification", "No source link is available for this discovered breakdown.")
        parsed = urlparse(opportunity.original_post_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return self._fail("External Link Verification", "Source link is not a valid web URL.")
        return self._pass("External Link Verification", "Title opens the exact source URL supplied for this breakdown.")

    def _breakdown_type_check(self, opportunity: Opportunity) -> dict:
        if opportunity.breakdown_classification in REJECTED_CLASSIFICATIONS:
            return self._fail(
                "Breakdown Type Verification",
                opportunity.rejection_reason or "Rejected because this is not an acting breakdown.",
            )
        classification = classify_breakdown_text(opportunity.description or "")
        if classification.classification in REJECTED_CLASSIFICATIONS:
            return self._fail(
                "Breakdown Type Verification",
                classification.rejection_reason or "Rejected because this listing does not ask for performers.",
            )
        if opportunity.breakdown_classification not in ACTOR_FACING_CLASSIFICATIONS:
            if opportunity.source_type in {"Manual Entry", "Agent Submission", "Direct Email"}:
                return self._warn("Breakdown Type Verification", "Manual breakdown needs a quick review because the type is not fully confirmed.")
            return self._warn("Breakdown Type Verification", "Needs Review: performer-role signals were not confidently found.")
        return self._pass("Breakdown Type Verification", "This listing is classified as an acting breakdown.")

    def _role_eligibility_check(self, opportunity: Opportunity) -> dict:
        if opportunity.visibility_status == "discarded" and opportunity.hidden_by_rule in {
            "dealbreaker_role_type",
            "dealbreaker_demographic_mismatch",
            "dealbreaker_eligibility",
        }:
            return self._fail("Role Eligibility Verification", opportunity.hidden_reason or "Role eligibility failed saved actor rules.")
        if opportunity.demographic_match_status == "Not a Match":
            return self._fail(
                "Role Eligibility Verification",
                opportunity.demographic_match_explanation
                or "Rejected because the role requirements do not overlap the saved actor profile.",
            )
        if opportunity.demographic_match_status == "Needs Review":
            return self._warn("Role Eligibility Verification", "Needs Review: role eligibility is not fully verified yet.")
        return self._pass("Role Eligibility Verification", "Role requirements pass saved actor rules.")

    def _audition_location_check(self, opportunity: Opportunity) -> dict:
        if opportunity.audition_type != "In-Person":
            return self._pass("Audition Location Verification", "Audition travel is not required for self-tape or virtual auditions.")
        if not opportunity.audition_location and not self._explicit_audition_location(opportunity):
            return self._warn("Audition Location Verification", "Needs audition location before travel can be calculated.")
        if opportunity.hidden_by_rule == "audition_location_needs_info":
            return self._warn("Audition Location Verification", opportunity.hidden_reason or "Needs audition location.")
        if opportunity.visibility_status == "travel_exception":
            return self._warn("Audition Location Verification", opportunity.hidden_reason or "Audition is outside saved travel preference.")
        return self._pass("Audition Location Verification", "Audition travel uses an explicit audition location.")

    def _date_checks(self, opportunity: Opportunity) -> list[dict]:
        checks = []
        labels = {
            "submission_due_date": opportunity.submission_deadline,
            "audition_date": opportunity.audition_deadline,
            "callback_date": opportunity.callback_date,
            "shoot_start_date": opportunity.shoot_start_date,
            "shoot_end_date": opportunity.shoot_end_date,
        }
        populated = {key: self._date_value(value) for key, value in labels.items() if value}
        if not populated:
            checks.append(self._warn("Date Verification", "No submission, audition, callback, or work dates were found."))
            return checks
        duplicates = {}
        for key, value in populated.items():
            duplicates.setdefault(value, []).append(key)
        conflated = [names for names in duplicates.values() if len(names) > 1]
        if conflated:
            checks.append(
                self._warn(
                    "Date Verification",
                    "Some dates are identical across different date fields. Confirm posted, due, audition, callback, and work dates separately.",
                )
            )
        else:
            checks.append(self._pass("Date Verification", "Dates are stored in separate submission, audition, callback, and work fields."))
        return checks

    def _platform_check(self, opportunity: Opportunity) -> dict:
        source_name = opportunity.source.name if opportunity.source else ""
        platform = f"{opportunity.platform or ''} {source_name}".lower()
        if any(name in platform for name in PROTECTED_PLATFORMS):
            if opportunity.source_type in {"Manual Entry", "Agent Submission", "Direct Email"} or (opportunity.source_metadata or {}).get("user_imported"):
                return self._pass("Platform Verification", "Protected platform data was user-entered or user-imported.")
            return self._warn(
                "Platform Verification",
                "Do not assume private platform data is available unless the actor manually enters or imports it.",
            )
        return self._pass("Platform Verification", "No protected casting platform access is assumed.")

    def _contact_check(self, opportunity: Opportunity) -> dict:
        details = opportunity.production_details or {}
        contact_values = [details.get("casting_office"), details.get("casting_director"), details.get("casting_contact")]
        if opportunity.casting_office_id or opportunity.casting_contact_id or any(contact_values):
            text = " ".join(str(item or "") for item in contact_values + [opportunity.description]).lower()
            if "casting" not in text and not opportunity.casting_office_id and not opportunity.casting_contact_id:
                return self._warn("Contact Verification", "Needs Review: contact information was not explicitly labeled as casting.")
            return self._pass("Contact Verification", "Casting contact or office is explicitly linked or labeled.")
        return self._warn("Contact Verification", "No casting office or casting contact is listed.")

    def _source_category_check(self, opportunity: Opportunity) -> dict:
        source_category = str((opportunity.source_metadata or {}).get("source_classification") or opportunity.category or "")
        if any(term in source_category.lower() for term in ["placeholder", "dead", "rejected"]):
            return self._fail("Source Category Verification", "Rejected because the source is not a usable breakdown source.")
        return self._pass("Source Category Verification", "Source category does not indicate a dead, placeholder, or rejected source.")

    def _duplicate_check(self, opportunity: Opportunity) -> dict:
        if opportunity.is_duplicate:
            return self._warn("Duplicate Verification", "Possible duplicate. Confirm project title, role name, dates, and source before merging.")
        return self._pass("Duplicate Verification", "No duplicate flag is set for this record.")

    def _ai_inference_check(self, opportunity: Opportunity) -> dict:
        if opportunity.ai_inference:
            return self._pass("AI Inference Labeling", "AI-generated interpretation is stored separately from extracted facts.")
        return self._warn("AI Inference Labeling", "No AI interpretation is stored yet. Recommendations should stay deterministic or suggested.")

    def _confidence_check(self, opportunity: Opportunity) -> dict:
        confidence = self._parse_confidence(opportunity)
        if confidence is not None and confidence < 70:
            return self._warn("Confidence Threshold", "Needs Review: parse confidence is below 70%. Ask only for missing details.")
        if opportunity.confidence_level == "Low":
            return self._warn("Confidence Threshold", "Needs Info: confidence is low, so this should not be over-recommended.")
        return self._pass("Confidence Threshold", "Confidence is high enough for normal display.")

    def _deletion_check(self, opportunity: Opportunity) -> dict:
        if opportunity.visibility_status == "discarded" or opportunity.status == "archived":
            return self._fail(
                "Deletion/Rejection Protection",
                opportunity.rejection_reason or opportunity.hidden_reason or "Rejected breakdown is removed from normal views.",
            )
        return self._pass("Deletion/Rejection Protection", "This breakdown has not been rejected or archived.")

    def _explicit_audition_location(self, opportunity: Opportunity) -> str | None:
        details = {**(opportunity.production_details or {}), **(opportunity.role_details or {})}
        for key in ["audition_location_name", "audition_address", "audition_location"]:
            value = details.get(key)
            if value:
                return str(value)
        return None

    def _parse_confidence(self, opportunity: Opportunity) -> float | None:
        metadata = opportunity.source_metadata or {}
        for key in ["breakdown_parse_confidence", "overall_confidence"]:
            try:
                if metadata.get(key) is not None:
                    return float(metadata[key])
            except (TypeError, ValueError):
                return None
        if opportunity.breakdown_parse_runs:
            return float(opportunity.breakdown_parse_runs[0].overall_confidence)
        return None

    def _date_value(self, value: datetime | date) -> str:
        if isinstance(value, datetime):
            return value.date().isoformat()
        return value.isoformat()

    def _pass(self, name: str, reason: str) -> dict:
        return {"name": name, "status": "pass", "reason": reason}

    def _warn(self, name: str, reason: str) -> dict:
        return {"name": name, "status": "warning", "reason": reason}

    def _fail(self, name: str, reason: str) -> dict:
        return {"name": name, "status": "fail", "reason": reason}
