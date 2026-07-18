export const queryStaleTimes = {
  live: 15_000,
  workflow: 60_000,
  reference: 5 * 60_000,
  configuration: 10 * 60_000
} as const;
