import type {
  ActorCommandCenter,
  CareerMemory,
  CommandCenterCard,
  DailyPlatformCheckIn,
  ExecutiveBrief,
  ExecutivePriority
} from "../../../types/domain";

export type ChiefOfStaffPriority = ExecutivePriority;
export type PriorityType = ExecutivePriority["category"];
export type SinceLastVisitSummary = CommandCenterCard;
export type MeaningfulChange = CommandCenterCard;
export type WeeklyBrief = ExecutiveBrief;
export type ChiefOfStaffMemory = CareerMemory;
export type FocusRecommendation = CommandCenterCard;
export type ChiefOfStaffAlert = CommandCenterCard;
export type CheckInRecommendation = DailyPlatformCheckIn;
export type ChiefOfStaffArchiveEntry = ExecutiveBrief;

export type ChiefOfStaffSummary = {
  priorities: ChiefOfStaffPriority[];
  sinceLastVisit: SinceLastVisitSummary[];
  upcomingAttention: CommandCenterCard[];
  todayCareerRecommendation?: CommandCenterCard | null;
  platformCheckIns: DailyPlatformCheckIn[];
};

export type ChiefOfStaffCompactInput = {
  commandCenter: ActorCommandCenter | null;
};

export type ChiefOfStaffMemoryPayload = {
  current_career_goals: string[];
  current_focus: string | null;
  stretch_archetypes: string[];
  preferred_project_types: string[];
  preferred_markets: string[];
  unavailable_dates: string[];
  career_notes: string | null;
  executive_notes: string | null;
};
