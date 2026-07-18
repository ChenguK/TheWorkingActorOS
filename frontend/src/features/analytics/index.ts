export { AnalyticsPanel } from "./components/AnalyticsPanel";
export { CastingPatternsPanel } from "./components/CastingPatternsPanel";
export { MaterialPerformancePanel } from "./components/MaterialPerformancePanel";
export type {
  AnalyticsDateRange,
  CastingPatternDashboard,
  CastingPatternInsight,
  CostSummary,
  DataSufficiencyState,
  PatternStage
} from "./types";
export * from "./api";
export { analyticsKeys, useIndustryTrends, useIntelligenceDashboard, useMaterialPerformance, useOperationsDashboard } from "./hooks/useAnalyticsQueries";
