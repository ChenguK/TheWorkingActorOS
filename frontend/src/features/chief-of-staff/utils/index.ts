import type { ChiefOfStaffCompactInput, ChiefOfStaffSummary } from "../types";

export function getChiefOfStaffPriorities(data: ChiefOfStaffCompactInput) {
  return data.commandCenter?.chief_of_staff_priorities ?? data.commandCenter?.executive_priorities ?? [];
}

export function getSinceLastVisitChanges(data: ChiefOfStaffCompactInput) {
  return data.commandCenter?.since_last_visit ?? [];
}

export function getChiefOfStaffSummary(data: ChiefOfStaffCompactInput): ChiefOfStaffSummary {
  return {
    priorities: getChiefOfStaffPriorities(data),
    sinceLastVisit: getSinceLastVisitChanges(data),
    upcomingAttention: data.commandCenter?.upcoming_attention ?? [],
    todayCareerRecommendation: data.commandCenter?.today_career_recommendation ?? null,
    platformCheckIns: data.commandCenter?.platform_check_ins ?? []
  };
}

export function getPlatformCheckInRecommendationText(data: ChiefOfStaffCompactInput) {
  const unchecked = (data.commandCenter?.platform_check_ins ?? []).filter(
    (checkIn) => checkIn.active && checkIn.has_subscription && !checkIn.checked_today
  );
  if (unchecked.length === 0) return null;
  const names = unchecked.map((checkIn) => checkIn.platform_name).join(", ");
  return `${names} ${unchecked.length === 1 ? "has" : "have"} not been manually checked today.`;
}
