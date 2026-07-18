export function formatDateTime(value: unknown) {
  if (!value || typeof value !== "string") return "None";
  return new Date(value).toLocaleString();
}
