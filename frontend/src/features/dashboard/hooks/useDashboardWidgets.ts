import { useEffect, useMemo, useState } from "react";
import type { DashboardWidget } from "../types";
import { moveDashboardWidget, sortWidgets, toggleDashboardWidget } from "../utils";
import { useResetDashboardWidgets, useUpdateDashboardWidgets } from "./useDashboardQueries";

type DashboardDragEndEvent = {
  active: { id: string | number };
  over?: { id: string | number } | null;
};

export function useDashboardWidgets({ initialWidgets }: { initialWidgets: DashboardWidget[] }) {
  const [widgets, setWidgets] = useState<DashboardWidget[]>(initialWidgets);
  const saveWidgets = useUpdateDashboardWidgets();
  const resetWidgets = useResetDashboardWidgets();
  const [mutationError, setMutationError] = useState<unknown>(null);

  useEffect(() => {
    setWidgets(initialWidgets);
  }, [initialWidgets]);

  const widgetById = useMemo(() => Object.fromEntries(widgets.map((widget) => [widget.widget_id, widget])), [widgets]);
  const enabledWidgets = useMemo(
    () => widgets.filter((widget) => widget.enabled).sort(sortWidgets),
    [widgets]
  );
  const enabledIds = enabledWidgets.map((widget) => widget.widget_id);

  async function persist(nextWidgets: DashboardWidget[]) {
    if (saveWidgets.isPending) return;
    const previous = widgets;
    setWidgets(nextWidgets);
    setMutationError(null);
    try {
      await saveWidgets.mutateAsync(nextWidgets);
    } catch (error) {
      setWidgets(previous);
      setMutationError(error);
      throw error;
    }
  }

  async function onDragEnd(event: DashboardDragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = enabledWidgets.findIndex((widget) => widget.widget_id === active.id);
    const newIndex = enabledWidgets.findIndex((widget) => widget.widget_id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const reorderedEnabled = moveDashboardWidget(enabledWidgets, oldIndex, newIndex);
    const disabled = widgets.filter((widget) => !widget.enabled).sort(sortWidgets);
    await persist([...reorderedEnabled, ...disabled]);
  }

  async function toggleWidget(widgetId: string, enabled: boolean) {
    await persist(toggleDashboardWidget(widgets, widgetId, enabled));
  }

  async function resetLayout() {
    if (resetWidgets.isPending) return;
    const previous = widgets;
    setMutationError(null);
    try {
      setWidgets(await resetWidgets.mutateAsync());
    } catch (error) {
      setWidgets(previous);
      setMutationError(error);
      throw error;
    }
  }

  return {
    enabledIds,
    enabledWidgets,
    onDragEnd,
    resetLayout,
    toggleWidget,
    widgetById,
    widgets,
    mutationError,
    mutationPending: saveWidgets.isPending || resetWidgets.isPending
  };
}
