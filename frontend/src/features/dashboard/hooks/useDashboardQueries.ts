import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "../../../services/api/queryKeys";
import { queryStaleTimes } from "../../../services/api/queryPolicy";
import type { DashboardWidget, FocusModeName } from "../types";
import { getFocusMode, listDashboardWidgets, resetDashboardWidgets, saveDashboardWidgets, updateFocusMode } from "../api";

export const dashboardKeys = {
  widgets: queryKeys.dashboard.list({ resource: "widgets" }),
  focusMode: queryKeys.dashboard.list({ resource: "focusMode" })
} as const;

const options = { staleTime: queryStaleTimes.configuration };
export const useDashboardWidgetQuery = () => useQuery({ queryKey: dashboardKeys.widgets, queryFn: listDashboardWidgets, ...options });
export const useFocusMode = () => useQuery({ queryKey: dashboardKeys.focusMode, queryFn: getFocusMode, ...options });

function useInvalidate(queryKey: readonly unknown[]) {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey });
}

export function useUpdateDashboardWidgets() {
  const invalidate = useInvalidate(dashboardKeys.widgets);
  return useMutation({ mutationFn: (widgets: DashboardWidget[]) => saveDashboardWidgets(widgets), onSuccess: invalidate });
}

export function useResetDashboardWidgets() {
  const invalidate = useInvalidate(dashboardKeys.widgets);
  return useMutation({ mutationFn: resetDashboardWidgets, onSuccess: invalidate });
}

export function useUpdateFocusMode() {
  const invalidate = useInvalidate(dashboardKeys.focusMode);
  return useMutation({ mutationFn: (mode: FocusModeName) => updateFocusMode(mode), onSuccess: invalidate });
}
