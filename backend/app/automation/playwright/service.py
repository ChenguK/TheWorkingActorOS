from __future__ import annotations


class PlaywrightAutomationService:
    """Boundary for browser automation.

    The MVP uses mock execution only. Real integrations should implement this
    interface with explicit source-specific safety and terms review.
    """

    def prepare(self, payload: dict) -> dict:
        return {"status": "prepared", "payload": payload}

    def execute_mock(self, payload: dict) -> list[dict]:
        return [
            {"step": "open_submission_target", "status": "ok"},
            {"step": "select_or_attach_assets", "status": "ok", "assets": payload.get("assets", {})},
            {"step": "fill_submission_note", "status": "ok"},
            {"step": "pause_before_final_submit", "status": "ok"},
            {"step": "mock_submit_after_user_approval", "status": "ok"},
        ]

