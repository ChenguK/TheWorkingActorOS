export type {
  CostDashboard as CostSummary,
  IndustryTrendDashboard as CastingPatternDashboard,
  IndustryTrendInsight as CastingPatternInsight,
  IntelligenceDashboard,
  MaterialPerformance,
  OperationsDashboard,
  SystemCapabilities
} from "../../../types/domain";

export type AnalyticsDateRange = "All Time" | "This Quarter" | "This Year";
export type DataSufficiencyState = "Configured" | "Early Recommendation" | "Insufficient Data" | "Add Data First" | string;
export type PatternStage = "Early Signals" | "Emerging Patterns" | "Stronger Patterns" | string;

