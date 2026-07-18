import unittest

from app.services.breakdown_intelligence_engine import BreakdownIntelligenceEngine


STRUCTURED_BREAKDOWN = """
Production Details
Project: TRIANGULO
Union: AEA
Project Type: Theater / Musical Theater

Audition Information
Self-tape due Friday. Callbacks will be virtual.

Preparation
Prepare one contemporary musical theater or Latin-pop song.

Esperança (lead)

Raised in Rio de Janeiro during the rise of Brazilian Jiu-Jitsu and mixed martial arts in the early 1990s, Esperança possesses both physical grit and profound emotional sensitivity.

Female, Brazilian, should read late teens, 5’5” and under;

Contemporary musical theatre or Latin-pop/jazz belt-mix vocalist

Comfort with movement-based performance is essential; experience with dance, martial arts, stage combat, or athletic training is highly valued, especially Brazilian Jiu-Jitsu, judo, other grappling arts, or MMA.

Guillermo (lead)

Guillermo is charismatic, disciplined, and sensitive. He’s a musician with a dream.

Male, Cuban, should read age 20

Tenor or high-baritone with strong contemporary musical theatre and/or Latin-pop/jazz sensibility.
"""

EPA_BREAKDOWN = """
EPA
Equity Principal Audition

AUDITION DATE
Thursday, July 9, 2026
10:00 AM - 6:00 PM

LOCATION
Ripley-Grier Studios
305 W 38th St
New York, NY

PREPARATION
Please prepare two brief contrasting selections. Bring a picture and resume.

PERSONNEL
Casting: Example Casting

SEEKING
Equity actors for principal roles in a new play.
"""


class BreakdownIntelligenceEngineTests(unittest.TestCase):
    def test_standard_parse_detects_sections_and_roles(self):
        parsed = BreakdownIntelligenceEngine().parse(STRUCTURED_BREAKDOWN)

        section_types = {section["section_type"] for section in parsed["sections"]}
        roles = parsed["details"]["role_details"]["available_roles"]

        self.assertIn("Production Details", section_types)
        self.assertIn("Audition Information", section_types)
        self.assertIn("Preparation", section_types)
        self.assertIn("Roles", section_types)
        self.assertGreaterEqual(parsed["overall_confidence"], 70)
        self.assertEqual([role["role_name"] for role in roles], ["Esperança", "Guillermo"])
        self.assertEqual(roles[0]["ethnicity"], "Brazilian")
        self.assertEqual(roles[1]["gender_presentation"], "Male")

    def test_low_information_parse_is_flagged_for_review(self):
        parsed = BreakdownIntelligenceEngine().parse("Actor needed.")

        self.assertLess(parsed["overall_confidence"], 70)
        self.assertEqual(parsed["sections"][0]["section_type"], "Additional Notes")

    def test_epa_parse_extracts_theater_specific_fields(self):
        parsed = BreakdownIntelligenceEngine().parse(EPA_BREAKDOWN)

        details = parsed["details"]
        section_types = {section["section_type"] for section in parsed["sections"]}

        self.assertEqual(details["production_details"]["project_type"], "Theatre")
        self.assertEqual(details["production_details"]["union_status"], "Equity")
        self.assertIsNone(details["production_details"]["shooting_location"])
        self.assertEqual(details["production_details"]["audition_date"], "July 9, 2026")
        self.assertEqual(details["production_details"]["audition_time"], "10:00 AM - 6:00 PM")
        self.assertEqual(details["production_details"]["audition_location_name"], "Ripley-Grier Studios")
        self.assertEqual(details["production_details"]["audition_address"], "305 W 38th St, New York, NY")
        self.assertEqual(details["role_details"]["audition_type"], "In-Person")
        self.assertEqual(details["role_details"]["audition_subtype"], "EPA")
        self.assertIn("Please prepare two brief contrasting selections", details["role_details"]["preparation"])
        self.assertIn("Dates", section_types)
        self.assertIn("Locations", section_types)
        self.assertIn("Preparation", section_types)


if __name__ == "__main__":
    unittest.main()
