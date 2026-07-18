from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import DashboardWidget, FocusModePreference

VALID_FOCUS_MODES = {
    "Audition Mode",
    "Career Building Mode",
    "Casting Goals Mode",
    "Relationship Mode",
    "Analytics Mode",
}

DEFAULT_DASHBOARD_WIDGETS = [
    ("executive_top_priorities", "Chief of Staff: Top 3", True, 0, "large"),
    ("since_last_visit", "Since Your Last Visit", True, 1, "large"),
    ("platform_check_in", "Today's Platform Check-In", True, 2, "medium"),
    ("todays_priorities", "Priority Breakdowns", False, 3, "large"),
    ("self_tapes_due", "Self-Tapes Due", True, 4, "medium"),
    ("upcoming_deadlines", "Upcoming Deadlines", True, 5, "medium"),
    ("new_opportunities", "New Breakdowns", True, 6, "medium"),
    ("career_development_tasks", "Career Development Tasks", True, 7, "medium"),
    ("material_recommendations", "Material Recommendations", True, 8, "medium"),
    ("career_insight", "Career Insight", True, 9, "medium"),
    ("casting_goals", "Casting Goals", True, 10, "medium"),
    ("quick_actions", "Quick Actions", True, 11, "large"),
    ("industry_trends", "Your Casting Patterns", True, 12, "medium"),
    ("readiness_score", "Readiness Score", True, 13, "medium"),
    ("quarterly_progress", "Quarterly Progress", True, 14, "medium"),
    ("upcoming_callbacks", "Upcoming Callbacks", False, 15, "medium"),
    ("strong_matches", "Strong Matches", False, 16, "medium"),
    ("growth_matches", "Growth Matches", False, 17, "medium"),
    ("stretch_matches", "Stretch Matches", False, 18, "medium"),
    ("asset_freshness_warnings", "Asset Freshness Warnings", False, 19, "medium"),
    ("audition_calendar_preview", "Audition Calendar Preview", False, 20, "medium"),
    ("analytics_snapshot", "Analytics Snapshot", False, 21, "medium"),
    ("relationship_reminders", "Relationship Reminders", False, 22, "medium"),
]

VALID_WIDGET_IDS = {widget_id for widget_id, *_ in DEFAULT_DASHBOARD_WIDGETS}
VALID_WIDGET_SIZES = {"small", "medium", "large"}


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def list_widgets(self, actor_profile_id: UUID | None = None) -> list[DashboardWidget]:
        self.ensure_default_widgets(actor_profile_id)
        statement = self._base_statement(actor_profile_id).order_by(
            DashboardWidget.sort_order.asc(), DashboardWidget.display_name.asc()
        )
        return list(self.db.scalars(statement))

    def update_widgets(
        self, updates: list[dict], actor_profile_id: UUID | None = None
    ) -> list[DashboardWidget]:
        self.ensure_default_widgets(actor_profile_id)
        widgets = {widget.widget_id: widget for widget in self.db.scalars(self._base_statement(actor_profile_id))}
        for update in updates:
            widget_id = update["widget_id"]
            if widget_id not in VALID_WIDGET_IDS or widget_id not in widgets:
                continue
            widget = widgets[widget_id]
            if update.get("enabled") is not None:
                widget.enabled = update["enabled"]
            if update.get("sort_order") is not None:
                widget.sort_order = update["sort_order"]
            if update.get("size") is not None and update["size"] in VALID_WIDGET_SIZES:
                widget.size = update["size"]
        self.db.commit()
        return self.list_widgets(actor_profile_id)

    def reset_widgets(self, actor_profile_id: UUID | None = None) -> list[DashboardWidget]:
        self.db.execute(
            delete(DashboardWidget).where(DashboardWidget.actor_profile_id == actor_profile_id)
            if actor_profile_id
            else delete(DashboardWidget).where(DashboardWidget.actor_profile_id.is_(None))
        )
        self.db.commit()
        self.ensure_default_widgets(actor_profile_id)
        return self.list_widgets(actor_profile_id)

    def get_focus_mode(self, actor_profile_id: UUID | None = None) -> FocusModePreference:
        preference = self.db.scalars(self._focus_statement(actor_profile_id)).first()
        if preference:
            return preference
        preference = FocusModePreference(actor_profile_id=actor_profile_id, active_mode="Audition Mode")
        self.db.add(preference)
        self.db.commit()
        self.db.refresh(preference)
        return preference

    def update_focus_mode(self, active_mode: str, actor_profile_id: UUID | None = None) -> FocusModePreference:
        if active_mode not in VALID_FOCUS_MODES:
            active_mode = "Audition Mode"
        preference = self.get_focus_mode(actor_profile_id)
        preference.active_mode = active_mode
        self.db.commit()
        self.db.refresh(preference)
        return preference

    def ensure_default_widgets(self, actor_profile_id: UUID | None = None) -> None:
        existing_widgets = {
            widget.widget_id: widget
            for widget in self.db.scalars(self._base_statement(actor_profile_id))
        }
        for widget_id, display_name, enabled, sort_order, size in DEFAULT_DASHBOARD_WIDGETS:
            if widget_id in existing_widgets:
                existing_widgets[widget_id].display_name = display_name
                continue
            self.db.add(
                DashboardWidget(
                    actor_profile_id=actor_profile_id,
                    widget_id=widget_id,
                    display_name=display_name,
                    enabled=enabled,
                    sort_order=sort_order,
                    size=size,
                )
            )
        self.db.commit()

    @staticmethod
    def _base_statement(actor_profile_id: UUID | None):
        statement = select(DashboardWidget)
        if actor_profile_id:
            return statement.where(DashboardWidget.actor_profile_id == actor_profile_id)
        return statement.where(DashboardWidget.actor_profile_id.is_(None))

    @staticmethod
    def _focus_statement(actor_profile_id: UUID | None):
        statement = select(FocusModePreference)
        if actor_profile_id:
            return statement.where(FocusModePreference.actor_profile_id == actor_profile_id)
        return statement.where(FocusModePreference.actor_profile_id.is_(None))
