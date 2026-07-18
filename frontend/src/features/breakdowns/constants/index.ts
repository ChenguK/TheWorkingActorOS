import type { DiscoverySearchMode, Opportunity } from "../types";

export const sourceTypes: Opportunity["source_type"][] = [
  "Platform Discovery",
  "Agent Submission",
  "Direct Email",
  "Social Media",
  "Production Website",
  "Manual Entry",
  "Other"
];

export const sourceTypeLabel = (type: Opportunity["source_type"] | string) =>
  type === "Platform Discovery" ? "Platform Breakdown" : type;

export const discoverySearchModes: DiscoverySearchMode[] = [
  "Match My Profile",
  "Match My Archetypes",
  "Find Stretch Roles",
  "Search Specific Archetype"
];
