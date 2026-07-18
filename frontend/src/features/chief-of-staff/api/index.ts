import { api } from "../../../services/api";
import type { ActorCommandCenter, CareerMemory, DailyPlatformCheckIn, ExecutiveBrief } from "../../../types/domain";
import type { ChiefOfStaffMemoryPayload } from "../types";

export function refreshCommandCenter() {
  return api.post<ActorCommandCenter>("/command-center/refresh");
}

export function getCommandCenter() {
  return api.get<ActorCommandCenter>("/command-center");
}

export function updatePlatformCheckIn(subscriptionId: string, checkedToday: boolean) {
  return api.patch<DailyPlatformCheckIn>(`/operations/platform-check-ins/today/${subscriptionId}`, {
    checked_today: checkedToday,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York"
  });
}

export function generateWeeklyBrief() {
  return api.post<ExecutiveBrief>("/agents/chief-of-staff/briefs/weekly");
}

export function listExecutiveBriefs() {
  return api.get<ExecutiveBrief[]>("/agents/chief-of-staff/briefs");
}

export function updateChiefOfStaffMemory(payload: ChiefOfStaffMemoryPayload) {
  return api.put<CareerMemory>("/agents/career-memory", payload);
}

export function resolveOutcomeNudge(nudgeId: string) {
  return api.post<{ status: string }>(`/command-center/outcome-nudges/${nudgeId}/resolve`);
}
