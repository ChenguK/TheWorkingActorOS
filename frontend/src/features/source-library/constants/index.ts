import type { SourceResearchCategory, SourceResearchItem } from "../../../types/domain";

export const sourceResearchCategories: SourceResearchCategory[] = [
  "Public casting site",
  "Casting office",
  "Film commission",
  "Social media account",
  "Production company",
  "Theater company",
  "Talent platform",
  "Other"
];

export const sourceResearchStatuses: SourceResearchItem["status"][] = [
  "Suggested",
  "Researching",
  "Approved",
  "Active",
  "Paused",
  "Deleted"
];

export const sourceClassificationOptions = [
  "Valid Breakdown Source",
  "Casting Office",
  "Production Company",
  "Regional Resource",
  "Watch List Source",
  "Not Useful",
  "Rejected",
  "Needs Review"
] as const;

export const sourceUsefulnessOptions = [
  "Useful Breakdown Source",
  "Useful Non-Breakdown Source",
  "Not Useful",
  "Needs Review"
] as const;

export const badSourceHealth = [
  "Placeholder Website",
  "Dead / Unavailable Domain",
  "No Meaningful Content"
];

