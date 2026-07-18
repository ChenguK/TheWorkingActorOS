from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, Asset, Opportunity
from app.repositories.opportunity import MAIN_BREAKDOWN_CLASSIFICATIONS


ROLE_ARCHETYPE_KEYWORDS: dict[str, list[str]] = {
    "Authority Figure": ["authority", "chief", "director", "leader", "supervisor", "boss", "official"],
    "Attorney": ["attorney", "lawyer", "legal", "court", "judge", "prosecutor", "defense"],
    "Detective": ["detective", "investigator", "police", "case", "crime", "federal agent"],
    "Executive": ["executive", "ceo", "founder", "corporate", "board", "business"],
    "Journalist": ["journalist", "reporter", "news", "anchor", "media"],
    "Teacher": ["teacher", "professor", "principal", "school", "student"],
    "Nurse": ["nurse", "doctor", "hospital", "medical", "clinic", "patient"],
    "Parent": ["parent", "mother", "mom", "father", "dad", "family"],
    "Political Leader": ["political", "senator", "mayor", "campaign", "staffer", "governor"],
    "Blue Collar": ["mechanic", "worker", "driver", "construction", "warehouse"],
    "Comedy": ["comedy", "comic", "funny", "sitcom"],
    "Dramatic Guest Star": ["drama", "dramatic", "guest star", "procedural"],
}


class MaterialMatchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_matches(
        self,
        actor: ActorProfile,
        asset_id: UUID | None = None,
        include_hidden: bool = False,
        min_score: int = 15,
    ) -> list[dict]:
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        if asset_id:
            assets = [asset for asset in assets if asset.id == asset_id]
        if not assets:
            return []

        query = select(Opportunity).where(Opportunity.status == "open").where(Opportunity.is_demo_data.is_(False))
        if not include_hidden:
            query = query.where(Opportunity.visibility_status == "visible")
            query = query.where(Opportunity.breakdown_classification.in_(MAIN_BREAKDOWN_CLASSIFICATIONS))
        opportunities = list(self.db.scalars(query.order_by(Opportunity.created_at.desc())))

        matches = [
            result
            for opportunity in opportunities
            if (result := self._score_opportunity(opportunity, assets))["score"] >= min_score
        ]
        return sorted(matches, key=lambda item: (item["score"], item["opportunity"].created_at), reverse=True)

    def _score_opportunity(self, opportunity: Opportunity, assets: list[Asset]) -> dict:
        opportunity_terms = self._opportunity_terms(opportunity)
        matched_assets = []
        all_terms: set[str] = set()
        present_types: set[str] = set()
        score = 0

        for asset in assets:
            asset_terms = self._asset_terms(asset)
            matched_terms = sorted(asset_terms.intersection(opportunity_terms))
            inferred_matches = sorted(set(asset.archetype_names).intersection(self._inferred_archetypes(opportunity)))
            terms = sorted(set(matched_terms + inferred_matches))
            if not terms:
                continue

            present_types.add(asset.asset_type)
            all_terms.update(terms)
            type_bonus = {"Headshot": 18, "Reel": 22, "Resume": 14, "Slate": 10}.get(asset.asset_type, 8)
            term_bonus = min(18, len(terms) * 4)
            score += type_bonus + term_bonus
            matched_assets.append(
                {
                    "asset_id": asset.id,
                    "asset_name": asset.asset_name,
                    "asset_type": asset.asset_type,
                    "matched_terms": terms,
                    "reason": f"{asset.asset_name} supports this role through {', '.join(terms[:6])}.",
                }
            )

        if opportunity.audition_type in {"Self-Tape", "Virtual"}:
            score += 5
        if opportunity.priority in {"High", "Urgent"}:
            score += 5
        if opportunity.role_type:
            score += 3

        score = min(100, score)
        missing = [asset_type for asset_type in ["Headshot", "Reel", "Resume", "Slate"] if asset_type not in present_types]
        match_type = "Strong Material Match" if score >= 70 else "Good Material Match" if score >= 45 else "Possible Material Match"
        explanation = self._explanation(opportunity, matched_assets, all_terms, missing)
        return {
            "opportunity": opportunity,
            "score": score,
            "match_type": match_type,
            "matched_assets": matched_assets,
            "matched_terms": sorted(all_terms),
            "missing_material_types": missing,
            "explanation": explanation,
        }

    def _opportunity_terms(self, opportunity: Opportunity) -> set[str]:
        text = " ".join(
            [
                opportunity.role,
                opportunity.project,
                opportunity.project_type or "",
                opportunity.role_type or "",
                opportunity.category or "",
                opportunity.description,
                *opportunity.archetypes,
                *self._inferred_archetypes(opportunity),
            ]
        )
        return self._terms(text)

    def _asset_terms(self, asset: Asset) -> set[str]:
        return self._terms(
            " ".join(
                [
                    asset.asset_name,
                    asset.description or "",
                    asset.original_filename or "",
                    *asset.tags,
                    *asset.archetype_names,
                    *asset.ai_suggested_tags,
                    *asset.ai_suggested_archetypes,
                ]
            )
        )

    def _inferred_archetypes(self, opportunity: Opportunity) -> list[str]:
        text = " ".join([opportunity.role, opportunity.role_type or "", opportunity.description]).lower()
        inferred = list(opportunity.archetypes)
        for archetype, keywords in ROLE_ARCHETYPE_KEYWORDS.items():
            if any(keyword in text for keyword in keywords) and archetype not in inferred:
                inferred.append(archetype)
        return inferred

    def _terms(self, text: str) -> set[str]:
        normalized = text.lower().replace("/", " ")
        words = {word for word in re.findall(r"[a-z][a-z0-9+-]{2,}", normalized)}
        phrases = {
            phrase.lower()
            for phrase in ROLE_ARCHETYPE_KEYWORDS
            if phrase.lower() in normalized
        }
        return words | phrases

    def _explanation(
        self,
        opportunity: Opportunity,
        matched_assets: list[dict],
        matched_terms: set[str],
        missing: list[str],
    ) -> str:
        if not matched_assets:
            return "No uploaded materials strongly match this role yet."
        materials = ", ".join(f"{asset['asset_name']} ({asset['asset_type']})" for asset in matched_assets[:4])
        terms = ", ".join(sorted(matched_terms)[:8])
        gap = f" Missing: {', '.join(missing)}." if missing else " Your core material package is represented."
        return f"{opportunity.role} matches uploaded materials including {materials}. Shared signals: {terms}.{gap}"
