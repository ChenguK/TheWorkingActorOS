import type { DashboardWidget } from "../types";

export function sortWidgets(a: DashboardWidget, b: DashboardWidget) {
  return a.sort_order - b.sort_order || a.display_name.localeCompare(b.display_name);
}

export function moveDashboardWidget(enabledWidgets: DashboardWidget[], oldIndex: number, newIndex: number) {
  const next = [...enabledWidgets];
  const [item] = next.splice(oldIndex, 1);
  next.splice(newIndex, 0, item);
  return next;
}

export function toggleDashboardWidget(widgets: DashboardWidget[], widgetId: string, enabled: boolean) {
  return widgets.map((widget) => widget.widget_id === widgetId ? { ...widget, enabled } : widget).sort(sortWidgets);
}
