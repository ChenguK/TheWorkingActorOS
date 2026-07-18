type QueryFilters = Readonly<Record<string, unknown>>;

function featureKeys<const Feature extends string>(feature: Feature) {
  const all = [feature] as const;
  return {
    all,
    lists: () => [...all, "list"] as const,
    list: <Filters extends QueryFilters>(filters?: Filters) => [...all, "list", filters ?? {}] as const,
    details: () => [...all, "detail"] as const,
    detail: (id: string) => [...all, "detail", id] as const
  };
}

export const queryKeys = {
  system: {
    capabilities: ["system", "capabilities"] as const
  },
  journal: featureKeys("journal"),
  calendar: featureKeys("calendar"),
  materials: featureKeys("materials"),
  relationships: featureKeys("relationships"),
  auditions: featureKeys("auditions"),
  sourceLibrary: featureKeys("sourceLibrary"),
  scriptFinder: featureKeys("scriptFinder"),
  breakdowns: featureKeys("breakdowns"),
  analytics: featureKeys("analytics"),
  career: featureKeys("career"),
  dashboard: featureKeys("dashboard"),
  chiefOfStaff: featureKeys("chiefOfStaff"),
  profile: featureKeys("profile"),
  settings: featureKeys("settings")
} as const;
