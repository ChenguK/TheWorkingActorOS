export function formatCurrency(value: number | null | undefined): string {
  return `$${Number(value ?? 0).toFixed(2)}`;
}

export function formatRate(value: number | null | undefined): string {
  return `${Math.round(Number(value ?? 0) * 100)}%`;
}

export function calculateCallbackBookingMetrics(submissions: import("../../../types/domain").Submission[]) {
  const callbackStatuses = new Set(["Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"]);
  const callbacks = submissions.filter((submission) => callbackStatuses.has(submission.current_status)).length;
  const bookings = submissions.filter((submission) => submission.current_status === "Booked").length;
  return {
    submissions: submissions.length,
    callbacks,
    bookings,
    callbackRate: submissions.length ? callbacks / submissions.length : 0,
    bookingRate: submissions.length ? bookings / submissions.length : 0
  };
}
