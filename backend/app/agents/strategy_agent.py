from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActorProfile, AgentRecommendation, Asset, LearningInsight, Opportunity, TravelPreference
from app.services.breakdown_deadline_service import BreakdownDeadlineService


AUTHORITY_ARCHETYPES = {
    "Attorney",
    "Detective",
    "Executive",
    "Journalist",
    "Teacher",
    "Nurse",
    "Political Leader",
    "Authority Figure",
}


class StrategyAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def analyze(self, opportunity: Opportunity, actor: ActorProfile) -> AgentRecommendation:
        date_result = BreakdownDeadlineService().apply_to_opportunity(opportunity)
        if date_result.expired or date_result.needs_review:
            explanation = date_result.reason or "This breakdown needs date review before recommendation."
            recommendation = AgentRecommendation(
                opportunity_id=opportunity.id,
                actor_profile_id=actor.id,
                score=0,
                match_type="High-Risk / High-Reward",
                display_opportunity=False,
                explanation=explanation,
                score_breakdown={
                    "role_fit": 0,
                    "production_travel": 0,
                    "audition_feasibility": 0,
                    "asset_package": 0,
                    "learning_signal": 0,
                },
                audition_type=opportunity.audition_type,
                audition_travel_hours=opportunity.audition_travel_hours,
                audition_decision="Not Recommended",
                audition_explanation=explanation,
                travel_explanation="Travel was not scored because deadline validation blocks recommendation.",
                archetype_explanation="Role fit was not scored because deadline validation blocks recommendation.",
                asset_explanation="No materials were recommended.",
                submission_strategy_explanation="Correct the deadline if the source was parsed incorrectly. Do not submit if the deadline has passed.",
                confidence_level=date_result.confidence,
                risk_level="High",
                risk_explanation=explanation,
                recommended_note="Not recommended until deadline validation passes.",
            )
            self.db.add(recommendation)
            self.db.commit()
            self.db.refresh(recommendation)
            return recommendation

        if opportunity.already_tracked:
            recommendation = AgentRecommendation(
                opportunity_id=opportunity.id,
                actor_profile_id=actor.id,
                score=0,
                match_type="High-Risk / High-Reward",
                display_opportunity=False,
                explanation="Already tracked. This breakdown already has a linked submission or audition in the system.",
                score_breakdown={
                    "role_fit": 0,
                    "production_travel": 0,
                    "audition_feasibility": 0,
                    "asset_package": 0,
                    "learning_signal": 0,
                },
                audition_type=opportunity.audition_type,
                audition_travel_hours=opportunity.audition_travel_hours,
                audition_decision="Already tracked",
                audition_explanation="The system found an existing submission for this breakdown.",
                travel_explanation="Travel was not rescored because duplicate submission prevention applies.",
                archetype_explanation="Role fit was not rescored because this is already tracked.",
                asset_explanation="Use the materials already saved with the linked submission unless updating the audition record.",
                submission_strategy_explanation="Do not submit again. View the existing submission, audition, or journal instead.",
                confidence_level="High",
                risk_level="Low",
                risk_explanation="Duplicate submission avoided.",
                recommended_note="Already tracked.",
            )
            self.db.add(recommendation)
            self.db.commit()
            self.db.refresh(recommendation)
            return recommendation

        role_fit_block = self._role_fit_block(opportunity)
        if role_fit_block:
            recommendation = AgentRecommendation(
                opportunity_id=opportunity.id,
                actor_profile_id=actor.id,
                score=10,
                match_type="High-Risk / High-Reward",
                display_opportunity=False,
                explanation=role_fit_block,
                score_breakdown={
                    "role_fit": -40,
                    "production_travel": 0,
                    "audition_feasibility": 0,
                    "asset_package": 0,
                    "learning_signal": 0,
                },
                audition_type=opportunity.audition_type,
                audition_travel_hours=opportunity.audition_travel_hours,
                audition_decision="Not Recommended",
                audition_explanation="No individual role in this breakdown currently fits the actor profile.",
                travel_explanation="Travel was not scored because role fit blocks a recommended submission.",
                archetype_explanation=role_fit_block,
                asset_explanation="No materials were recommended because the parsed roles do not fit.",
                submission_strategy_explanation=(
                    "Do not submit unless the actor manually overrides the role-fit screening."
                ),
                confidence_level="High",
                risk_level="High",
                risk_explanation=role_fit_block,
                recommended_note="Not recommended for submission based on parsed role eligibility.",
            )
            self.db.add(recommendation)
            self.db.commit()
            self.db.refresh(recommendation)
            return recommendation

        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        travel = self.db.scalars(
            select(TravelPreference).where(TravelPreference.actor_profile_id == actor.id)
        ).first()
        learning = self.db.scalars(
            select(LearningInsight)
            .where(LearningInsight.actor_profile_id == actor.id)
            .order_by(LearningInsight.created_at.desc())
            .limit(1)
        ).first()

        role_score, archetype_explanation, matched_archetypes = self._role_fit(opportunity, assets)
        travel_score, travel_explanation = self._production_travel(opportunity, travel)
        audition_score, display, audition_decision, audition_explanation = self._audition_feasibility(opportunity)
        asset_score, asset_explanation, recommendations = self._assets(assets, matched_archetypes)
        learning_score = self._learning_score(opportunity, learning)

        score_breakdown = {
            "role_fit": role_score,
            "production_travel": travel_score,
            "audition_feasibility": audition_score,
            "asset_package": asset_score,
            "learning_signal": learning_score,
        }
        score = max(0, min(100, sum(score_breakdown.values())))
        match_type = self._match_type(score, role_score, learning_score)
        note = self._note(opportunity, actor, match_type)
        risk_level, risk_explanation = self._risk(opportunity, score, display)
        confidence_level = self._confidence(score, recommendations, opportunity)
        explanation = (
            f"{match_type}. {archetype_explanation} {travel_explanation} {asset_explanation}"
        )
        recommendation = AgentRecommendation(
            opportunity_id=opportunity.id,
            actor_profile_id=actor.id,
            score=score,
            match_type=match_type,
            display_opportunity=display,
            explanation=explanation,
            score_breakdown=score_breakdown,
            audition_type=opportunity.audition_type,
            audition_travel_hours=opportunity.audition_travel_hours,
            audition_decision=audition_decision,
            audition_explanation=audition_explanation,
            travel_explanation=travel_explanation,
            archetype_explanation=archetype_explanation,
            asset_explanation=asset_explanation,
            submission_strategy_explanation=(
                "Submit with the assets that most closely reinforce the role archetype. "
                "Keep the note concise and specific to the project."
            ),
            confidence_level=confidence_level,
            risk_level=risk_level,
            risk_explanation=risk_explanation,
            recommended_headshot_id=recommendations.get("Headshot"),
            recommended_reel_id=recommendations.get("Reel"),
            recommended_resume_id=recommendations.get("Resume"),
            recommended_slate_id=recommendations.get("Slate"),
            recommended_note=note,
        )
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def _role_fit_block(self, opportunity: Opportunity) -> str | None:
        if not opportunity.breakdown_roles and (opportunity.role_details or {}).get("available_roles"):
            if opportunity.demographic_match_status == "Not a Match":
                return opportunity.demographic_match_explanation or "No individual role in this breakdown currently fits the actor profile."
        if not opportunity.breakdown_roles:
            return None
        fitting_roles = [
            role for role in opportunity.breakdown_roles if role.fit_status in {"Strong Fit", "Possible Fit", "Stretch Fit"}
        ]
        if fitting_roles:
            return None
        role_reasons = [
            f"{role.role_name}: {role.fit_explanation or 'Parsed requirements do not overlap the actor profile.'}"
            for role in opportunity.breakdown_roles
        ]
        return "No parsed role is currently a fit. " + " ".join(role_reasons)

    def _role_fit(self, opportunity: Opportunity, assets: list[Asset]) -> tuple[int, str, list[str]]:
        character_archetypes = [
            str(archetype)
            for role in opportunity.breakdown_roles
            if role.fit_status in {"Strong Fit", "Possible Fit", "Stretch Fit"} and role.character_profile
            for archetype in [
                *(role.character_profile.primary_archetypes or []),
                *(role.character_profile.secondary_archetypes or []),
            ]
        ]
        text = f"{opportunity.role} {opportunity.description}".lower()
        role_archetypes = character_archetypes or [item for item in AUTHORITY_ARCHETYPES if item.lower() in text]
        asset_archetypes = {item for asset in assets for item in asset.archetype_names}
        matched = sorted(set(role_archetypes).intersection(asset_archetypes))
        if matched:
            return 30, f"Archetype fit is strong because character intelligence aligns the role with {', '.join(matched)}.", matched
        if role_archetypes:
            return 20, f"Character intelligence suggests {', '.join(role_archetypes)}, but matching assets are limited.", role_archetypes
        return 16, "The role has broad casting language, so archetype fit is moderate.", []

    def _production_travel(self, opportunity: Opportunity, travel: TravelPreference | None) -> tuple[int, str]:
        hours = opportunity.audition_travel_hours
        if opportunity.travel_covered and opportunity.housing_covered:
            return 20, "Production travel is favorable because travel and housing are covered."
        if hours is not None and travel and hours <= travel.max_local_drive_time / 60:
            return 18, "Production travel appears local based on configured drive-time settings."
        if opportunity.travel_covered:
            return 12, "Production travel is partially feasible because travel is covered."
        return 8, "Production travel needs review because coverage is unclear or unavailable."

    def _audition_feasibility(self, opportunity: Opportunity) -> tuple[int, bool, str, str]:
        if opportunity.audition_type == "Self-Tape":
            return 15, True, "Eligible", "Self-tape auditions are always evaluated using normal role scoring."
        hours = opportunity.audition_travel_hours
        if hours is None:
            return 5, True, "Eligible", "In-person audition travel time is unknown, so the opportunity remains visible for review."
        if hours <= 2:
            return 15, True, "Eligible", f"In-person audition travel is {hours:.1f} hours, within the 2-hour threshold."
        return -30, False, "Not Eligible", "Audition exceeds maximum in-person audition travel threshold."

    def _assets(self, assets: list[Asset], matched_archetypes: list[str]) -> tuple[int, str, dict[str, object]]:
        recommendations: dict[str, object] = {}
        for asset_type in ["Headshot", "Reel", "Resume", "Slate"]:
            candidates = [asset for asset in assets if asset.asset_type == asset_type]
            if not candidates:
                continue
            recommendations[asset_type] = self._best_asset(candidates, matched_archetypes).id
        score = min(20, 5 * len(recommendations))
        missing = [asset_type for asset_type in ["Headshot", "Reel", "Resume", "Slate"] if asset_type not in recommendations]
        if missing:
            return score, f"Asset package is partial; missing recommended {', '.join(missing)}.", recommendations
        return score, "Asset package is complete across headshot, reel, resume, and slate.", recommendations

    def _best_asset(self, assets: list[Asset], matched_archetypes: list[str]) -> Asset:
        return max(
            assets,
            key=lambda asset: len(set(asset.archetype_names).intersection(matched_archetypes))
            + len(asset.tags),
        )

    def _learning_score(self, opportunity: Opportunity, learning: LearningInsight | None) -> int:
        if not learning:
            return 5
        text = f"{opportunity.role} {opportunity.description}".lower()
        for role in opportunity.breakdown_roles:
            profile = role.character_profile
            if not profile:
                continue
            text += " " + " ".join(
                str(item)
                for item in [
                    *(profile.primary_archetypes or []),
                    *(profile.secondary_archetypes or []),
                    *(profile.personality_traits or []),
                    *(profile.emotional_traits or []),
                ]
            ).lower()
        user_boosted = learning.recommendation_weights.get("user_boosted_reasons", [])
        user_stretch = learning.recommendation_weights.get("user_stretch_reasons", [])
        user_suppressed = learning.recommendation_weights.get("user_suppressed_reasons", [])
        if any(str(item).lower() in text for item in user_suppressed):
            return -10
        if any(str(item).lower() in text for item in user_boosted):
            return 15
        if any(str(item).lower() in text for item in user_stretch):
            return 10
        boosted = learning.recommendation_weights.get("boosted_archetypes", [])
        return 10 if any(item.lower() in text for item in boosted) else 5

    def _match_type(self, score: int, role_score: int, learning_score: int) -> str:
        if score >= 75:
            return "Strong Match"
        if role_score >= 20 or learning_score >= 10:
            return "Growth Match"
        return "High-Risk / High-Reward"

    def _note(self, opportunity: Opportunity, actor: ActorProfile, match_type: str) -> str:
        return (
            f"Hi, I would love to be considered for {opportunity.role} in {opportunity.project}. "
            f"My materials are tailored for this {match_type.lower()} and I am available for the requested audition workflow."
        )

    def _confidence(self, score: int, recommendations: dict[str, object], opportunity: Opportunity) -> str:
        if score >= 75 and len(recommendations) >= 3 and opportunity.confidence_level == "High":
            return "High"
        if score >= 55 and len(recommendations) >= 2:
            return "Medium"
        return "Low"

    def _risk(self, opportunity: Opportunity, score: int, display: bool) -> tuple[str, str]:
        if not display:
            return "High", "Audition feasibility prevents this opportunity from being shown in the main queue."
        if opportunity.risk_level == "High" or score < 45:
            return "High", opportunity.risk_explanation or "Low match score or incomplete logistics require caution."
        if opportunity.risk_level == "Medium" or score < 65:
            return "Medium", opportunity.risk_explanation or "Some fit or logistics details should be reviewed before submission."
        return "Low", "Recommendation has strong fit signals and no major known logistics risk."
