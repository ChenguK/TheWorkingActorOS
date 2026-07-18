import unittest

from app.services.casting_language_parser import CastingLanguageParser


class CastingLanguageParserTests(unittest.TestCase):
    def test_parses_tv_shorthand(self) -> None:
        parsed = CastingLanguageParser().parse("Co-Star / 40-60 / Woman / Any Ethnic Appearance")

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.original_text, "Co-Star / 40-60 / Woman / Any Ethnic Appearance")
        self.assertEqual(parsed.billing, "Co-Star")
        self.assertEqual(parsed.age_range, "40-60")
        self.assertEqual(parsed.gender, "Woman")
        self.assertEqual(parsed.ethnicity, "Any Ethnic Appearance")

    def test_parses_common_union_and_compensation_terms(self) -> None:
        parsed = CastingLanguageParser().parse("Lead / 30s / Female Presenting / Black / SAG-AFTRA / $1,200/day")

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.billing, "Lead")
        self.assertEqual(parsed.age_range, "30s")
        self.assertEqual(parsed.gender, "Female Presenting")
        self.assertEqual(parsed.ethnicity, "Black")
        self.assertEqual(parsed.union, "SAG-AFTRA")
        self.assertEqual(parsed.compensation, "$1,200/day")

    def test_keeps_unparsed_notes(self) -> None:
        parsed = CastingLanguageParser().parse("Voiceover / Any Gender / Non-Union / strong improv skills")

        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.billing, "Voiceover")
        self.assertEqual(parsed.gender, "Any Gender")
        self.assertEqual(parsed.union, "Non-Union")
        self.assertIn("strong improv skills", parsed.special_notes)


if __name__ == "__main__":
    unittest.main()
