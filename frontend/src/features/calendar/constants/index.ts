export function colorForCalendarEvent(eventType: string): string {
  if (eventType === "Self-Tape Due" || eventType === "Submission Due") return "#2563eb";
  if (eventType === "Virtual Callback" || eventType === "In-Person Callback" || eventType.includes("Callback")) return "#7c3aed";
  if (eventType === "Fitting") return "#db2777";
  if (eventType === "Shoot") return "#0f766e";
  return "#475569";
}
