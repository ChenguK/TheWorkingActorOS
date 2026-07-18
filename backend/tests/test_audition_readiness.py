import unittest

from app.db.models import BreakdownRole, CharacterProfile, Opportunity
from app.services.intelligence_service import IntelligenceService


class AuditionReadinessTests(unittest.TestCase):
    def test_readiness_uses_character_intelligence_archetypes(self) -> None:
        opportunity = Opportunity(
            role="Viv",
            project="I'm Sorry, Matt 06",
            description="Protective mother with comedy and warm PTA energy.",
        )
        role = BreakdownRole(role_name="Viv", fit_status="Possible Fit", fit_score=72)
        role.character_profile = CharacterProfile(
            role_name="Viv",
            primary_archetypes=["Mom", "PTA Mom", "Protective Mother"],
            secondary_archetypes=["Comedy", "Warm Authority"],
            archetype_confidence_scores=[
                {"archetype": "Mom", "confidence": 90, "tier": "Primary", "evidence": ["mother"]},
                {"archetype": "Comedy", "confidence": 82, "tier": "Secondary", "evidence": ["comedy"]},
            ],
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

        service = IntelligenceService(db=None)

        self.assertEqual(service._best_breakdown_role(opportunity), role)
        self.assertEqual(
            service._character_archetypes(role.character_profile),
            ["Mom", "PTA Mom", "Protective Mother", "Comedy", "Warm Authority"],
        )
        self.assertIn("PTA Mom", service._readiness_role_text(opportunity, role, service._character_archetypes(role.character_profile)))

    def test_missing_character_intelligence_requests_better_parsing(self) -> None:
        service = IntelligenceService(db=None)

        self.assertEqual(service._character_archetypes(None), [])
        self.assertEqual(service._character_archetype_confidence(None), 0)
        self.assertEqual(service._readiness_label(70, None, character_ready=False), "Needs Materials")


if __name__ == "__main__":
    unittest.main()
