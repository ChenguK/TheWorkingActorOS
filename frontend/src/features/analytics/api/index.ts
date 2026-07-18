import { api } from "../../../services/api";
import type { IndustryTrendDashboard, IntelligenceDashboard, MaterialPerformance, OperationsDashboard } from "../../../types/domain";

export function getOperationsDashboard() {
  return api.get<OperationsDashboard>("/operations/dashboard");
}

export function getIntelligenceDashboard() {
  return api.get<IntelligenceDashboard>("/intelligence/dashboard");
}

export function getCastingPatterns() {
  return api.get<IndustryTrendDashboard>("/intelligence/casting-patterns");
}

export function getMaterialPerformance() {
  return api.get<MaterialPerformance[]>("/intelligence/materials/performance");
}
