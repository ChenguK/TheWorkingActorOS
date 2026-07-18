import { api } from "../../../services/api";
import type { DashboardWidget, FocusModeName, FocusModePreference } from "../../../types/domain";

export function listDashboardWidgets() {
  return api.get<DashboardWidget[]>("/dashboard/widgets");
}

export function resetDashboardWidgets() {
  return api.post<DashboardWidget[]>("/dashboard/widgets/reset");
}

export function saveDashboardWidgets(widgets: DashboardWidget[]) {
  return api.put<DashboardWidget[]>("/dashboard/widgets", {
    widgets: widgets.map((widget, index) => ({
      widget_id: widget.widget_id,
      enabled: widget.enabled,
      sort_order: index,
      size: widget.size
    }))
  });
}

export function getFocusMode() {
  return api.get<FocusModePreference>("/dashboard/focus-mode");
}

export function updateFocusMode(activeMode: FocusModeName) {
  return api.put<FocusModePreference>("/dashboard/focus-mode", { active_mode: activeMode });
}
