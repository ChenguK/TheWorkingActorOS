from pathlib import Path


ROOT = Path(__file__).resolve().parents[1].parent
CALENDAR_PAGE = ROOT / "frontend/src/pages/CalendarPage.tsx"
ACTOR_CALENDAR = ROOT / "frontend/src/features/calendar/components/ActorCalendar.tsx"
CALENDAR_HOOK = ROOT / "frontend/src/features/calendar/hooks/useActorCalendar.ts"
CALENDAR_QUERY_HOOKS = ROOT / "frontend/src/features/calendar/hooks/useCalendarQueries.ts"
CALENDAR_UTILS = ROOT / "frontend/src/features/calendar/utils/index.ts"
CALENDAR_INDEX = ROOT / "frontend/src/features/calendar/index.ts"
TOP_NAVIGATION = ROOT / "frontend/src/layout/TopNavigation.tsx"


def test_calendar_page_is_composition_layer():
    text = CALENDAR_PAGE.read_text()

    assert 'import { ActorCalendar } from "@/features/calendar"' in text
    assert "FullCalendar" not in text
    assert "createCalendarEvent" not in text
    assert "buildFullCalendarEvents" not in text
    assert len(text.splitlines()) <= 40


def test_calendar_feature_owns_fullcalendar_and_event_form():
    component = ACTOR_CALENDAR.read_text()
    hook = CALENDAR_HOOK.read_text()
    query_hooks = CALENDAR_QUERY_HOOKS.read_text()
    utils = CALENDAR_UTILS.read_text()

    assert "FullCalendar" in component
    assert 'initialView="dayGridMonth"' in component
    assert "timeGridWeek" in component
    assert "timeGridDay" in component
    assert "Add Calendar Event" in component
    assert "Upcoming Calendar Items" in component
    assert "Availability" in component
    assert "Add Availability Block" in component
    assert "useCreateAvailabilityBlock" in component
    assert "window.prompt" not in component
    assert "prompt(" not in component
    assert "Self-tapes" in component
    assert "Shoots / performances" in component
    assert "useCreateCalendarEvent" in hook
    assert "useUpdateCalendarEvent" in hook
    assert "useDeleteCalendarEvent" in hook
    assert "createCalendarEvent" in query_hooks
    assert "updateCalendarEvent" in query_hooks
    assert "deleteCalendarEvent" in query_hooks
    assert "onChanged" not in hook
    assert "window.open(`/auditions?breakdownId=${opportunityId}`" in hook
    assert "buildFullCalendarEvents" in utils
    assert "platform-check-in" in utils


def test_calendar_public_api_exports_actor_calendar_boundary():
    text = CALENDAR_INDEX.read_text()

    assert "ActorCalendar" in text
    assert "useActorCalendar" in text
    assert "../../pages/CalendarPage" not in text


def test_calendar_page_does_not_consume_calendar_workflow_snapshot():
    text = CALENDAR_PAGE.read_text()

    assert "data.calendarEvents" not in text
    assert "data.availabilityBlocks" not in text
    assert "data.onChanged" not in text


def test_calendar_internals_do_not_import_pages_or_workflow_panels():
    internal_roots = [
        ROOT / "frontend/src/features/calendar/components",
        ROOT / "frontend/src/features/calendar/hooks",
        ROOT / "frontend/src/features/calendar/utils",
        ROOT / "frontend/src/features/calendar/types",
        ROOT / "frontend/src/features/calendar/constants",
    ]
    for root in internal_roots:
      for path in root.rglob("*.ts*"):
          text = path.read_text()
          assert "workflowPanels" not in text
          assert "pages/CalendarPage" not in text


def test_calendar_stays_in_top_navigation():
    text = TOP_NAVIGATION.read_text()

    assert '{ label: "Calendar", to: "/calendar" }' in text
