import unittest

from app.services.capability_service import CapabilityService


class CapabilityServiceTests(unittest.TestCase):
    def test_system_capabilities_exposes_flags_states_and_truth_labels(self):
        class DummyCapabilityService(CapabilityService):
            def __init__(self):
                pass

            def flags(self):
                return {
                    "travel_provider_configured": False,
                    "ai_configured": False,
                    "scheduler_configured": False,
                    "notifications_configured": False,
                    "source_discovery_configured": False,
                    "public_profile_import_configured": True,
                }

            def feature_states(self):
                return {
                    "ai_assisted_tagging": {
                        "state": "Not Configured",
                        "explanation": "Uses deterministic suggestions until AI is configured.",
                        "safe_fallback": "Suggested Tags",
                    }
                }

            def integration_statuses(self, flags=None):
                return [
                    {
                        "id": "openai",
                        "name": "OpenAI API",
                        "status": "Not Configured",
                        "configured": False,
                        "what_it_enables": "AI-assisted tagging and LLM parsing.",
                        "fallback_behavior": "Deterministic suggestions.",
                        "setup_instructions": "Set OPENAI_API_KEY in the backend .env.",
                    }
                ]

        payload = DummyCapabilityService().system_capabilities()

        self.assertFalse(payload["flags"]["ai_configured"])
        self.assertTrue(payload["flags"]["public_profile_import_configured"])
        self.assertEqual(payload["states"]["ai_assisted_tagging"]["safe_fallback"], "Suggested Tags")
        self.assertEqual(payload["integrations"][0]["name"], "OpenAI API")
        self.assertNotIn("api_key", payload["integrations"][0])
        self.assertEqual(payload["labels"]["not_configured"], "Not Configured")
        self.assertEqual(payload["labels"]["dashboard_alerts_only"], "Dashboard Alerts Only")


if __name__ == "__main__":
    unittest.main()
