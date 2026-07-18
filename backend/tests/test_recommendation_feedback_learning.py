import unittest

from app.agents.strategy_agent import StrategyAgent
from app.db.models import BreakdownRole, CharacterProfile, LearningInsight, Opportunity


class RecommendationFeedbackLearningTests(unittest.TestCase):
    def opportunity_with_archetype(self, archetype: str) -> Opportunity:
        opportunity = Opportunity(
            role="Viv",
            project="Comedy Pilot",
            union="SAG-AFTRA",
            location="Los Angeles, CA",
            description="Warm mom with comedy and emotional range.",
        )
        role = BreakdownRole(role_name="Viv", fit_status="Possible Fit")
        role.character_profile = CharacterProfile(
            role_name="Viv",
            primary_archetypes=[archetype],
            secondary_archetypes=[],
            archetype_confidence_scores=[],
            personality_traits=[],
            emotional_traits=[],
            relationships=[],
            motivations=[],
            comedic_level=0,
            dramatic_level=0,
            physical_requirements=[],
            vocal_requirements=[],
            movement_requirements=[],
            casting_language=[],
            recommended_materials=[],
        )
        opportunity.breakdown_roles.append(role)
        return opportunity

    def test_user_positive_feedback_boosts_future_recommendations(self) -> None:
        learning = LearningInsight(
            actor_profile_id=None,
            trends={},
            recommendation_weights={
                "user_boosted_reasons": ["Mom"],
                "user_feedback_weight": 3,
                "boosted_archetypes": [],
            },
            explanation="",
        )

        score = StrategyAgent(db=None)._learning_score(self.opportunity_with_archetype("Mom"), learning)

        self.assertEqual(score, 15)

    def test_not_my_type_feedback_suppresses_future_recommendations(self) -> None:
        learning = LearningInsight(
            actor_profile_id=None,
            trends={},
            recommendation_weights={
                "user_suppressed_reasons": ["Detective"],
                "user_feedback_weight": 3,
                "boosted_archetypes": ["Detective"],
            },
            explanation="",
        )

        score = StrategyAgent(db=None)._learning_score(self.opportunity_with_archetype("Detective"), learning)

        self.assertEqual(score, -10)


if __name__ == "__main__":
    unittest.main()
