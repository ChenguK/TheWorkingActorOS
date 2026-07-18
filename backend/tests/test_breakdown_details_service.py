import unittest

from app.db.models import ActorProfile, Opportunity
from app.agents.strategy_agent import StrategyAgent
from app.services.breakdown_details_service import BreakdownDetailsService
from app.services.breakdown_role_service import BreakdownRoleService
from app.services.demographic_match_service import DemographicMatchService


TRIANGULO_TEXT = """
Esperança (lead)

Raised in Rio de Janeiro during the rise of Brazilian Jiu-Jitsu and mixed martial arts in the early 1990s, Esperança possesses both physical grit-although physically small-and profound emotional sensitivity.

Female, Brazilian, should read late teens, 5’5” and under;

Contemporary musical theatre or Latin-pop/jazz belt-mix vocalist

Comfort with movement-based performance is essential; experience with dance, martial arts, stage combat, or athletic training is highly valued, especially Brazilian Jiu-Jitsu, judo, other grappling arts, or MMA.

Portuguese and/or Spanish language familiarity is a plus but not required.

Guillermo (lead)

Guillermo is charismatic, disciplined, and sensitive. He’s a musician with a dream. Esperança both fascinates and threatens him because she possesses qualities he recognizes in himself: hunger, intelligence, instinct, and ambition.

Male, Cuban, should read age 20

Tenor or high-baritone with strong contemporary musical theatre and/or Latin-pop/jazz sensibility.

Experience with movement and dance is highly valuable.

The ability to play guitar is a plus.
"""

HAPPY_TEXT = """
HAPPY:
[Female Presenting | 20–30 | Black]
A bold personality with exceptional comedic instincts, confident, lovable, and a total scene-stealer.
Dynamic singer with a brassy old-school tone, belt moments, and legit musical theatre sound.
"""


class DummyDb:
    def flush(self):
        return None


class BreakdownDetailsServiceTests(unittest.TestCase):
    def test_playbill_multi_role_requirements_are_parsed(self):
        parsed = BreakdownDetailsService().from_text(TRIANGULO_TEXT)

        roles = parsed["role_details"]["available_roles"]

        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0]["role_name"], "Esperança")
        self.assertEqual(roles[0]["gender_presentation"], "Female")
        self.assertEqual(roles[0]["ethnicity"], "Brazilian")
        self.assertEqual(roles[0]["age_range"], "late teens")
        self.assertEqual(roles[0]["height_requirement"], "5’5” and under")
        self.assertIn("Brazilian Jiu-Jitsu", roles[0]["skills_required"])
        self.assertIn("martial arts", roles[0]["movement_requirements"])
        self.assertIn("Brazilian Jiu-Jitsu", roles[0]["special_skills"])
        self.assertEqual(parsed["production_details"]["project_type"], "Theater / Musical Theater")
        self.assertEqual(roles[1]["role_name"], "Guillermo")
        self.assertEqual(roles[1]["gender_presentation"], "Male")
        self.assertEqual(roles[1]["ethnicity"], "Cuban")
        self.assertEqual(roles[1]["age_range"], "20")

    def test_role_specific_demographic_match_detects_no_matching_roles(self):
        parsed = BreakdownDetailsService().from_text(TRIANGULO_TEXT)
        actor = ActorProfile(
            name="Actor",
            sag_status="SAG-AFTRA",
            union_status="Union",
            current_location="New York, NY",
            playable_age_min=30,
            playable_age_max=45,
            skills=[],
            gender_identities=["Woman / Female"],
            ethnicities=["Black / African American"],
            racial_identities=["Black / African American"],
            nationalities=["Sierra Leonean"],
            languages=["English"],
            accents=["Standard American"],
            disability_identities=[],
        )
        opportunity = Opportunity(
            role="Multiple Leads",
            project="Triangulo",
            union="Unknown",
            location="See source",
            description=TRIANGULO_TEXT,
            role_details=parsed["role_details"],
        )

        DemographicMatchService(db=None).apply(opportunity, actor)

        self.assertEqual(opportunity.demographic_match_status, "Not a Match")
        self.assertEqual(
            [role["status"] for role in opportunity.demographic_match_details["role_results"]],
            ["Not a Match", "Not a Match"],
        )

    def test_no_matching_roles_blocks_submit_ready_strategy(self):
        parsed = BreakdownDetailsService().from_text(TRIANGULO_TEXT)
        opportunity = Opportunity(
            role="Multiple Leads",
            project="Triangulo",
            union="Unknown",
            location="See source",
            description=TRIANGULO_TEXT,
            role_details=parsed["role_details"],
        )
        opportunity.demographic_match_status = "Not a Match"
        opportunity.demographic_match_explanation = "No parsed role fits this actor profile."

        explanation = StrategyAgent(db=None)._role_fit_block(opportunity)

        self.assertIn("No parsed role fits", explanation)

    def test_colon_bracket_role_is_parsed_and_scored_individually(self):
        parsed = BreakdownDetailsService().from_text(HAPPY_TEXT)
        roles = parsed["role_details"]["available_roles"]
        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0]["role_name"], "HAPPY")
        self.assertEqual(roles[0]["gender_presentation"], "Female Presenting")
        self.assertEqual(roles[0]["age_range"], "20–30")
        self.assertEqual(roles[0]["ethnicity"], "Black")
        self.assertIn("brassy", roles[0]["vocal_requirements"])
        self.assertIn("Comedy", roles[0]["archetypes"])
        self.assertEqual(roles[0]["extracted_facts"]["ethnicity_or_cultural_background"], "Black")
        self.assertEqual(roles[0]["ai_inference"]["likely_archetypes"]["explanation"], "Inferred from role description.")
        self.assertIn("extracted_facts", parsed)
        self.assertIn("ai_inference", parsed)

        actor = ActorProfile(
            name="Actor",
            sag_status="SAG-AFTRA",
            union_status="Union",
            current_location="New York, NY",
            playable_age_min=25,
            playable_age_max=35,
            skills=[],
            gender_identities=["Woman / Female"],
            ethnicities=["Black / African American"],
            racial_identities=["Black / African American"],
            nationalities=[],
            languages=["English"],
            accents=["Standard American"],
            disability_identities=[],
        )
        opportunity = Opportunity(
            role="HAPPY",
            project="Demo Musical",
            union="AEA",
            location="New York, NY",
            description=HAPPY_TEXT,
            role_details=parsed["role_details"],
        )
        DemographicMatchService(db=None).apply(opportunity, actor)
        BreakdownRoleService(DummyDb()).sync_from_details(opportunity)

        self.assertEqual(opportunity.demographic_match_status, "Match")
        self.assertEqual(len(opportunity.breakdown_roles), 1)
        synced_role = opportunity.breakdown_roles[0]
        self.assertIn(synced_role.fit_status, {"Strong Fit", "Possible Fit"})
        self.assertGreaterEqual(synced_role.fit_score, 70)
        self.assertIn("Playable Age", synced_role.fit_explanation)
        self.assertEqual(synced_role.extracted_facts["ethnicity_or_cultural_background"], "Black")
        self.assertIn("compatibility across demographics", synced_role.ai_inference["fit_score"]["explanation"])


if __name__ == "__main__":
    unittest.main()
