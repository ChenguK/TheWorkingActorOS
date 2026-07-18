export function humanCapabilityName(value: string) {
  if (value === "industry_trend_analysis") return "Your Casting Patterns";
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
