from __future__ import annotations

from app.automation.playwright.service import PlaywrightAutomationService


class SubmissionAdapter:
    adapter_key: str
    submission_mode: str

    def prepare(self, recommendation) -> dict:
        raise NotImplementedError

    def execute(self, payload: dict) -> list[dict]:
        raise NotImplementedError


class MockPlatformManagedAdapter(SubmissionAdapter):
    adapter_key = "mock_platform_managed"
    submission_mode = "Platform Managed Assets"

    def __init__(self) -> None:
        self.browser = PlaywrightAutomationService()

    def prepare(self, recommendation) -> dict:
        return self.browser.prepare(
            {
                "mode": self.submission_mode,
                "assets": {
                    "headshot_id": str(recommendation.recommended_headshot_id) if recommendation.recommended_headshot_id else None,
                    "reel_id": str(recommendation.recommended_reel_id) if recommendation.recommended_reel_id else None,
                    "resume_id": str(recommendation.recommended_resume_id) if recommendation.recommended_resume_id else None,
                    "slate_id": str(recommendation.recommended_slate_id) if recommendation.recommended_slate_id else None,
                },
                "note": recommendation.recommended_note,
            }
        )

    def execute(self, payload: dict) -> list[dict]:
        return self.browser.execute_mock(payload)


class MockDirectUploadAdapter(MockPlatformManagedAdapter):
    adapter_key = "mock_direct_upload"
    submission_mode = "Direct Upload"


class SubmissionAdapterRegistry:
    def __init__(self) -> None:
        self.adapters = {
            "mock_platform_managed": MockPlatformManagedAdapter(),
            "mock_direct_upload": MockDirectUploadAdapter(),
        }

    def choose(self, recommendation, submission_method: str | None = None) -> SubmissionAdapter:
        text = (submission_method or "").lower()
        if any(term in text for term in ["email", "form", "website", "google", "airtable"]):
            return self.adapters["mock_direct_upload"]
        return self.adapters["mock_platform_managed"]

    def get(self, adapter_key: str) -> SubmissionAdapter:
        return self.adapters[adapter_key]

