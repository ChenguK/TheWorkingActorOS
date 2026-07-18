import type { AssetType, AuditionCalendarEventType, SubmissionStatus } from "../types/domain";

export const assetTypes: AssetType[] = ["Headshot", "Reel", "Slate", "Resume"];

export const submissionStatuses: SubmissionStatus[] = [
  "Submitted",
  "Requested",
  "Self-Tape Callback",
  "In-Person Callback",
  "Pinned",
  "Booked",
  "Passed",
  "No Response"
];

export const selfTapeStatuses = ["Not Started", "In Progress", "Completed"];

export const calendarEventTypes: AuditionCalendarEventType[] = [
  "Submission Due",
  "Self-Tape Due",
  "Virtual Callback",
  "In-Person Callback",
  "Fitting",
  "Shoot",
  "Meeting",
  "Other"
];

export const callbackSubmissionStatuses = ["Requested", "Self-Tape Callback", "In-Person Callback", "Pinned", "Booked"];
export const closedSubmissionStatuses = ["Booked", "Passed", "No Response"];

export const defaultIncludedRoleTypes = [
  "Lead",
  "Supporting",
  "Principal",
  "Guest Star",
  "Co-Star",
  "Recurring",
  "Series Regular",
  "Voiceover",
  "Commercial Principal",
  "Theater Principal"
];

export const defaultExcludedRoleTypes = [
  "Background",
  "Extra",
  "Ensemble",
  "Brand Ambassador",
  "Class",
  "Workshop",
  "Seminar",
  "Crew",
  "Staff Job",
  "Internship",
  "Administrative Job"
];
