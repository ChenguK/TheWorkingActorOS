import unittest

from app.db.models import BreakdownRole, Opportunity
from app.services.character_intelligence_engine import CharacterIntelligenceEngine


class CharacterIntelligenceEngineTests(unittest.TestCase):
    def test_full_role_description_drives_character_interpretation(self) -> None:
        role = BreakdownRole(
            role_name="Esperança",
            billing="Lead",
            character_description=(
                "Raised in Rio de Janeiro during the rise of Brazilian Jiu-Jitsu and mixed martial arts, "
                "Esperança possesses physical grit and profound emotional sensitivity. She is instinctive, "
                "proud, stubborn, and deeply resilient, carrying the tension between survival and vulnerability. "
                "Her journey confronts systems of power, gender expectations, family loyalty, immigration, and identity."
            ),
            gender_presentation="Female",
            ethnicity_or_cultural_background="Brazilian",
            vocal_requirements="Contemporary musical theatre or Latin-pop/jazz belt-mix vocalist",
            movement_requirements="Movement-based performance, dance, martial arts, stage combat, athletic training",
            special_skills="Brazilian Jiu-Jitsu, judo, grappling, MMA",
        )
        opportunity = Opportunity(
            role="Esperança",
            project="Triângulo",
            project_type="Theater / Musical Theater",
            union="AEA",
            location="New York, NY",
            description=role.character_description,
        )

        profile = CharacterIntelligenceEngine().profile_for_role(role, opportunity)

        self.assertIn("Survivor", profile["primary_archetypes"] + profile["secondary_archetypes"])
        self.assertIn("Fighter", profile["primary_archetypes"] + profile["secondary_archetypes"])
        self.assertIn("resilient", profile["personality_traits"])
        self.assertIn("vulnerable", profile["emotional_traits"])
        self.assertEqual(profile["genre"], "Musical Theater")
        self.assertGreaterEqual(profile["dramatic_level"], 70)
        self.assertTrue(profile["vocal_requirements"])
        self.assertTrue(profile["movement_requirements"])
        self.assertTrue(profile["casting_language"])
        self.assertIn("Vocal reel or musical theater selection", profile["recommended_materials"])

    def test_original_role_text_is_not_overwritten(self) -> None:
        description = "A confident attorney with a quiet moral conflict."
        role = BreakdownRole(role_name="Attorney", character_description=description)

        CharacterIntelligenceEngine().profile_for_role(role)

        self.assertEqual(role.character_description, description)

    def test_expands_parent_character_into_multiple_scored_archetypes(self) -> None:
        role = BreakdownRole(
            role_name="Viv",
            billing="Supporting",
            character_description=(
                "Viv is a warm, funny middle-class mom and PTA parent who protects her child, "
                "keeps the school community organized, believes in love, and offers emotional support "
                "while still carrying gentle authority."
            ),
        )

        profile = CharacterIntelligenceEngine().profile_for_role(role)
        archetypes = profile["primary_archetypes"] + profile["secondary_archetypes"]

        self.assertIn("Mom", archetypes)
        self.assertIn("Protective Mother", archetypes)
        self.assertIn("PTA Mom", archetypes)
        self.assertIn("Warm Authority", archetypes)
        self.assertIn("Middle-Class Parent", archetypes)
        self.assertIn("Comedy", archetypes)
        self.assertIn("Romantic Optimist", archetypes)
        self.assertIn("Emotional Caregiver", archetypes)
        self.assertIn("Supporting Character", archetypes)
        self.assertTrue(profile["archetype_confidence_scores"])
        self.assertTrue(all("confidence" in item for item in profile["archetype_confidence_scores"]))
        self.assertIn("Parent / warm family headshot", profile["recommended_materials"])


if __name__ == "__main__":
    unittest.main()
