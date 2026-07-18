import unittest

from app.services.skill_parser_service import SkillParserService


class SkillParserServiceTests(unittest.TestCase):
    def test_parses_resume_skill_categories(self):
        parser = SkillParserService()
        parsed = parser.parse_text(
            "Bike ride, Roller skate, Swim, Ballroom Dancing, Tap, Sing (Mezzo-Contralto/Belter), "
            "Dialects: Kenyan, Southern American, English, Valley Girl, New Yorker"
        )
        grouped = parser.grouped(parsed)

        self.assertIn("Bike Riding", grouped["Sports / Athletics"])
        self.assertIn("Roller skate", grouped["Sports / Athletics"])
        self.assertIn("Ballroom Dancing", grouped["Dance"])
        self.assertIn("Tap", grouped["Dance"])
        self.assertIn("Sing (Mezzo-Contralto/Belter)", grouped["Singing / Vocal"])
        self.assertIn("Kenyan", grouped["Accents / Dialects"])
        self.assertIn("New Yorker", grouped["Accents / Dialects"])

    def test_actor_skills_excludes_accents(self):
        parser = SkillParserService()
        parsed = parser.parse_items(["Soccer", "American - Southern Accent"])

        self.assertEqual(parser.actor_skills(parsed), ["Soccer"])
        self.assertEqual(parser.accents(parsed), ["American - Southern Accent"])


if __name__ == "__main__":
    unittest.main()
