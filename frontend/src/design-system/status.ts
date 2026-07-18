export type StatusTone = "neutral" | "info" | "success" | "warning" | "danger";

export const statusToneClasses: Record<StatusTone, string> = {
  neutral: "border-slate-200 bg-slate-100 text-slate-700",
  info: "border-blue-200 bg-blue-50 text-blue-900",
  success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  warning: "border-amber-200 bg-amber-50 text-amber-900",
  danger: "border-red-200 bg-red-50 text-red-700"
};

export function statusToneFromLabel(label: string | null | undefined): StatusTone {
  const normalized = String(label ?? "").toLowerCase();
  if (["complete", "completed", "configured", "active", "ready", "approved", "booked", "success"].some((word) => normalized.includes(word))) {
    return "success";
  }
  if (["warning", "needs", "review", "pending", "paused", "manual", "limited", "stretch"].some((word) => normalized.includes(word))) {
    return "warning";
  }
  if (["error", "failed", "rejected", "deleted", "not recommended", "danger", "blocked"].some((word) => normalized.includes(word))) {
    return "danger";
  }
  if (["info", "draft", "suggested", "not configured"].some((word) => normalized.includes(word))) {
    return "info";
  }
  return "neutral";
}
