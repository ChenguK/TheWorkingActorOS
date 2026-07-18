import type { CareerDevelopmentTask } from "../../../types/domain";

export function getDashboardQuickActionLinks(careerTasks: CareerDevelopmentTask[] = []) {
  const materialRecommended = careerTasks.some((task) =>
    task.status !== "Completed" && /headshot|reel|scene|slate|resume|material|self-tape/i.test(`${task.title} ${task.description} ${task.reason ?? ""}`)
  );
  return [
    { label: "Add Audition", to: "/auditions" },
    { label: "Import Breakdown", to: "/breakdowns" },
    { label: "Upload Material", to: "/materials" },
    { label: "Prepare Audition", to: "/auditions" },
    { label: "Create Career Task", to: "/career" },
    { label: "Generate Strategy", to: "/breakdowns" },
    { label: "Create Stretch Role Plan", to: "/career" },
    { label: "Generate Quarterly Review", to: "/career" },
    ...(materialRecommended ? [{ label: "Find Scene Options", to: "/career#script-reel-scene-finder" }] : [])
  ];
}

export function getPlatformCheckInSummary(data: { commandCenter: import("../../../types/domain").ActorCommandCenter | null }) {
  const checkIns = data.commandCenter?.platform_check_ins ?? [];
  return {
    checkedCount: checkIns.filter((item) => item.checked_today).length,
    totalCount: checkIns.length,
    platformNames: checkIns.map((item) => item.platform_name),
    safetyCopy: "Manual check-in only. The app does not log in, scrape, or submit."
  };
}
