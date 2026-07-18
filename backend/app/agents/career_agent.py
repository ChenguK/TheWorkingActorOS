from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    ActorProfile,
    Asset,
    BreakdownRole,
    CareerDevelopmentTask,
    CareerRecommendation,
    CareerSwotAnalysis,
    CastingGoal,
    Opportunity,
    Submission,
    WatchList,
)


STRETCH_ROLE_MAP = {
    "Attorney": ["Attorney", "Judge", "Legal Analyst", "Compliance Officer"],
    "Detective": ["Detective", "Investigator", "Federal Agent", "Internal Affairs"],
    "Executive": ["Corporate Executive", "Principal", "Hospital Administrator", "Executive Director"],
    "Journalist": ["Journalist", "Political Staffer", "University Dean", "Investigative Reporter"],
    "Political Leader": ["Mayor", "Campaign Director", "Political Leader", "Press Secretary"],
}
CALLBACK_STATUSES = {"Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"}
MATERIAL_TYPES = ["Headshot", "Reel", "Slate", "Resume", "Self-Tape Sample", "Scene Type"]


class CareerAgent:
    def __init__(self, db: Session) -> None:
        self.db = db

    def analyze(self, actor: ActorProfile) -> CareerRecommendation:
        assets = list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        submissions = list(
            self.db.scalars(
                select(Submission)
                .where(Submission.actor_profile_id == actor.id)
                .options(
                    selectinload(Submission.assets),
                    selectinload(Submission.opportunity)
                    .selectinload(Opportunity.breakdown_roles)
                    .selectinload(BreakdownRole.character_profile),
                )
            )
        )
        submissions = [
            submission
            for submission in submissions
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        asset_archetypes = Counter(item for asset in assets for item in asset.archetype_names)
        outcome_archetypes = self._outcome_archetypes(submissions)
        booking_roles = [
            submission.opportunity.role
            for submission in submissions
            if submission.current_status == "Booked" and submission.opportunity
        ]
        callback_roles = [
            submission.opportunity.role
            for submission in submissions
            if submission.current_status in CALLBACK_STATUSES and submission.opportunity
        ]
        strong_match_roles = self._strong_match_roles(booking_roles, callback_roles, asset_archetypes)
        growth_roles = self._growth_roles(asset_archetypes, outcome_archetypes)
        stretch_roles = self._stretch_roles(asset_archetypes, outcome_archetypes)
        active_goals = list(
            self.db.scalars(
                select(CastingGoal).where(CastingGoal.actor_profile_id == actor.id, CastingGoal.status == "Active")
            )
        )
        active_watch_lists = list(
            self.db.scalars(
                select(WatchList).where(WatchList.enabled.is_(True))
            )
        )
        goal_archetypes = [item for goal in active_goals for item in goal.target_archetypes]
        goal_role_types = [item for goal in active_goals for item in goal.target_role_types]
        watch_terms = [term for watch_list in active_watch_lists for term in watch_list.terms]
        watch_archetypes = [
            term
            for watch_list in active_watch_lists
            if watch_list.category in {"Archetypes", "Role Types", "Keywords", "Genres", "Shows"}
            for term in watch_list.terms
        ]
        for archetype in [*goal_archetypes, *watch_archetypes]:
            if archetype and archetype not in [role["archetype"] for role in stretch_roles]:
                stretch_roles.append(
                    {
                        "archetype": archetype,
                        "roles": goal_role_types[:4] or STRETCH_ROLE_MAP.get(archetype, [archetype]),
                        "confidence": "Priority-Driven",
                        "why": "Included because it appears in an active Casting Goal or Watch List.",
                        "material_gap_analysis": self._material_gap_analysis(archetype),
                    }
                )
        strengths = self._strengths(asset_archetypes, outcome_archetypes)
        expand = [role["archetype"] for role in stretch_roles]
        recommendation = CareerRecommendation(
            actor_profile_id=actor.id,
            strengths=strengths,
            growth_opportunities=growth_roles,
            archetypes_to_expand=expand,
            recommended_headshots=[
                {"archetype": name, "reason": f"Current library lacks a clear {name} image.", "priority": "High"}
                for name in expand[:4]
            ],
            recommended_role_types=[role for roles in STRETCH_ROLE_MAP.values() for role in roles][:8],
            strong_match_roles=strong_match_roles,
            growth_match_roles=growth_roles,
            stretch_roles=stretch_roles,
            explanation=(
                "Career guidance compares bookings, callbacks, current asset coverage, archetype usage, playable-age positioning, "
                "and stretch-role adjacency. Strong roles reflect proven traction; growth roles are adjacent to existing materials; "
                "stretch roles are plausible expansion targets that need new materials. Active Casting Goals are used as additional "
                f"career-priority context: {', '.join(goal.title for goal in active_goals) if active_goals else 'none set'}. "
                f"Active Watch Lists add discovery/material priority context: {', '.join(watch_terms[:8]) if watch_terms else 'none set'}."
            ),
        )
        self.db.add(recommendation)
        self.db.flush()
        for role in [*growth_roles[:3], *stretch_roles[:5]]:
            for task in self._tasks_for_role(recommendation.id, role):
                self.db.add(task)
        self.db.add(self.generate_swot(actor, assets, submissions, asset_archetypes, outcome_archetypes))
        self.db.commit()
        self.db.refresh(recommendation)
        return recommendation

    def generate_swot(
        self,
        actor: ActorProfile,
        assets: list[Asset] | None = None,
        submissions: list[Submission] | None = None,
        asset_archetypes: Counter[str] | None = None,
        outcome_archetypes: Counter[str] | None = None,
    ) -> CareerSwotAnalysis:
        assets = assets or list(self.db.scalars(select(Asset).where(Asset.actor_profile_id == actor.id)))
        submissions = submissions or list(
            self.db.scalars(
                select(Submission)
                .where(Submission.actor_profile_id == actor.id)
                .options(
                    selectinload(Submission.assets),
                    selectinload(Submission.opportunity)
                    .selectinload(Opportunity.breakdown_roles)
                    .selectinload(BreakdownRole.character_profile),
                )
            )
        )
        submissions = [
            submission
            for submission in submissions
            if not submission.opportunity or not submission.opportunity.is_demo_data
        ]
        asset_archetypes = asset_archetypes or Counter(item for asset in assets for item in asset.archetype_names)
        outcome_archetypes = outcome_archetypes or self._outcome_archetypes(submissions)
        strong = [name for name, _ in outcome_archetypes.most_common(3)] or [name for name, _ in asset_archetypes.most_common(3)]
        missing = [name for name in STRETCH_ROLE_MAP if name not in asset_archetypes]
        overused = [name for name, count in asset_archetypes.items() if count >= 3 and outcome_archetypes.get(name, 0) == 0]
        return CareerSwotAnalysis(
            actor_profile_id=actor.id,
            strengths=[
                f"{name} roles show traction or strong material coverage." for name in strong
            ] or ["Current asset library creates a foundation for targeted submissions."],
            weaknesses=[
                f"Limited {name} footage or image coverage." for name in missing[:3]
            ] or ["Outcome history is still developing, so recommendations need more signal."],
            opportunities=[
                f"Procedural and authority-based stretch lane: {name}." for name in missing[:3]
            ] or ["Use callback data to refine office-specific submission strategies."],
            threats=[
                f"Over-reliance on {name} without callback traction." for name in overused[:3]
            ] or ["Sparse feedback from casting can slow learning unless outcomes are updated consistently."],
            explanation=(
                "SWOT is generated from asset archetypes, manually tracked callbacks/bookings, missing material coverage, "
                "and over-represented archetypes without matching outcome signal."
            ),
        )

    def _outcome_archetypes(self, submissions: list[Submission]) -> Counter[str]:
        counter: Counter[str] = Counter()
        for submission in submissions:
            if submission.current_status in CALLBACK_STATUSES:
                for asset in submission.assets:
                    counter.update(asset.archetype_names)
                if submission.opportunity:
                    for role in submission.opportunity.breakdown_roles:
                        profile = role.character_profile
                        if not profile:
                            continue
                        for item in profile.archetype_confidence_scores or []:
                            archetype = item.get("archetype") if isinstance(item, dict) else None
                            confidence = int(item.get("confidence") or 0) if isinstance(item, dict) else 0
                            if archetype and confidence >= 65:
                                counter.update([str(archetype)])
        return counter

    def _strengths(self, asset_archetypes: Counter[str], outcome_archetypes: Counter[str]) -> list[str]:
        names = [name for name, _ in outcome_archetypes.most_common(4)]
        for name, _ in asset_archetypes.most_common(4):
            if name not in names:
                names.append(name)
        return names[:5]

    def _strong_match_roles(
        self, booking_roles: list[str], callback_roles: list[str], asset_archetypes: Counter[str]
    ) -> list[dict]:
        roles = Counter([*booking_roles, *callback_roles])
        if not roles:
            roles = Counter({role: 1 for archetype in asset_archetypes for role in STRETCH_ROLE_MAP.get(archetype, [archetype])})
        return [
            {
                "role": role,
                "match_type": "Strong Match",
                "why": "Aligned with existing bookings, callbacks, assets, or archetype coverage.",
                "missing_materials": [],
            }
            for role, _ in roles.most_common(5)
        ]

    def _growth_roles(self, asset_archetypes: Counter[str], outcome_archetypes: Counter[str]) -> list[dict]:
        candidates = []
        represented = set(asset_archetypes) | set(outcome_archetypes)
        for archetype in represented:
            for role in STRETCH_ROLE_MAP.get(archetype, [archetype]):
                candidates.append(
                    self._role_package(
                        archetype=archetype,
                        role=role,
                        match_type="Growth Match",
                        confidence="High" if outcome_archetypes.get(archetype, 0) else "Medium",
                        why="Adjacent to current assets, bookings, callbacks, or represented archetypes.",
                    )
                )
        return candidates[:6]

    def _stretch_roles(self, asset_archetypes: Counter[str], outcome_archetypes: Counter[str]) -> list[dict]:
        represented = set(asset_archetypes) | set(outcome_archetypes)
        return [
            self._role_package(
                archetype=archetype,
                role=roles[0],
                match_type="Stretch Role",
                confidence="High" if "Authority Figure" in asset_archetypes else "Medium",
                why=(
                    f"{archetype} is not strongly represented yet, but is plausible based on professional authority "
                    "positioning, playable-age casting patterns, and adjacent callback/material signals."
                ),
            )
            for archetype, roles in STRETCH_ROLE_MAP.items()
            if archetype not in represented
        ]

    def _role_package(self, archetype: str, role: str, match_type: str, confidence: str, why: str) -> dict:
        return {
            "role": role,
            "archetype": archetype,
            "match_type": match_type,
            "confidence": confidence,
            "missing_assets": self._missing_assets(archetype),
            "material_gap_analysis": self._material_gap_analysis(archetype),
            "recommendation": f"Build a targeted {archetype.lower()} material package for {role} submissions.",
            "expected_impact": "High" if archetype in {"Attorney", "Executive"} else "Medium",
            "why": why,
        }

    def _missing_assets(self, archetype: str) -> list[str]:
        if archetype == "Attorney":
            return ["New reel clip", "New scene type", "Attorney-specific slate"]
        if archetype == "Detective":
            return ["New self-tape sample", "New reel clip", "Detective-specific slate"]
        if archetype == "Executive":
            return ["New headshot", "Updated resume", "Executive reel clip"]
        return ["New headshot", "New reel clip", "New slate"]

    def _material_gap_analysis(self, archetype: str) -> list[dict]:
        return [
            {
                "material_type": material,
                "needed": material in self._missing_assets(archetype) or material in {"Headshot", "Reel", "Slate"},
                "reason": f"{material} helps casting immediately understand the {archetype} lane.",
            }
            for material in MATERIAL_TYPES
        ]

    def _tasks_for_role(self, recommendation_id, role: dict) -> list[CareerDevelopmentTask]:
        archetype = role["archetype"]
        supported_roles = STRETCH_ROLE_MAP.get(archetype, [archetype])
        tasks = []
        for missing in role["missing_assets"][:2]:
            tasks.append(
                CareerDevelopmentTask(
                    career_recommendation_id=recommendation_id,
                    title=self._task_title(archetype, missing),
                    description=(
                        f"Create {missing.lower()} for {archetype}. "
                        f"This supports {', '.join(supported_roles)} and can be linked to a new uploaded asset."
                    ),
                    priority="High" if role["expected_impact"] == "High" else "Medium",
                    estimated_impact=role["expected_impact"],
                    related_archetype=archetype,
                    target_role_types=supported_roles,
                    supported_archetypes=[archetype, "Authority Figure"],
                    reason=role["why"],
                    created_by_agent=True,
                )
            )
        return tasks

    def _task_title(self, archetype: str, material: str = "") -> str:
        if archetype == "Attorney" and "reel" in material.lower():
            return "Create Attorney Reel Scene"
        if archetype == "Detective" and ("self-tape" in material.lower() or "sample" in material.lower()):
            return "Film Detective Self-Tape"
        if archetype == "Political Leader" and "headshot" in material.lower():
            return "Create Political Leader Headshot"
        if archetype == "Executive" and "headshot" in material.lower():
            return "Create Authority Figure Headshot"
        return f"Create {archetype} {material or 'Materials'}"
