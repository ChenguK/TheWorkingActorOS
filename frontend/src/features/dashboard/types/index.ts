import type { ActorCommandCenter, DashboardWidget, DashboardWidgetSize, FocusModeName } from "../../../types/domain";

export type { DashboardWidget, DashboardWidgetSize, FocusModeName };

export type DashboardWidgetId = DashboardWidget["widget_id"];
export type DashboardWidgetLayout = Pick<DashboardWidget, "widget_id" | "enabled" | "sort_order" | "size">;
export type DashboardWidgetVisibility = Pick<DashboardWidget, "widget_id" | "enabled">;
export type DashboardNavigationTarget = "/" | "/auditions" | "/breakdowns" | "/materials" | "/career" | "/analytics" | "/relationships" | "/calendar" | "/journal" | "/profile" | "/settings" | string;
export type DashboardQuickAction = {
  label: string;
  to: DashboardNavigationTarget;
};
export type DashboardSummary = {
  metric: number | string;
  items: string[];
  empty: string;
};
export type PlatformCheckInState = NonNullable<ActorCommandCenter["platform_check_ins"]>[number];
