import type { FocusModeName } from "../types";

export const focusModes: FocusModeName[] = [
  "Audition Mode",
  "Career Building Mode",
  "Casting Goals Mode",
  "Relationship Mode",
  "Analytics Mode"
];

export const focusWidgetMap: Record<FocusModeName, string[]> = {
  "Audition Mode": ["executive_top_priorities", "since_last_visit", "platform_check_in", "todays_priorities", "self_tapes_due", "upcoming_deadlines", "readiness_score"],
  "Career Building Mode": ["executive_top_priorities", "since_last_visit", "platform_check_in", "career_insight", "career_development_tasks", "material_recommendations", "stretch_matches"],
  "Casting Goals Mode": ["executive_top_priorities", "since_last_visit", "platform_check_in", "casting_goals", "quick_actions", "stretch_matches", "growth_matches"],
  "Relationship Mode": ["executive_top_priorities", "since_last_visit", "platform_check_in", "relationship_reminders", "upcoming_callbacks", "career_insight"],
  "Analytics Mode": ["executive_top_priorities", "since_last_visit", "platform_check_in", "quarterly_progress", "industry_trends", "analytics_snapshot", "readiness_score"]
};
