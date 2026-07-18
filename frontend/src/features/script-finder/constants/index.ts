import type { SceneCandidate } from "../../../types/domain";

export const scriptRightsStatuses = ["Public Domain", "Royalty-Free", "Original / User-Owned", "Licensed", "Permission Required", "Unknown"];

export const scriptSourceTypes = ["Public domain", "Royalty-free scenes", "Original scenes", "Licensed database", "Rights-request platform", "Practice scene library", "Other"];

export const primarySceneResultTypes = ["Specific Scene", "Specific Monologue"];

export const resourceSceneResultTypes = ["Script Library", "Resource Guide"];

export const hiddenSceneResultTypes = ["Music / Sound Library", "Dead / Fetch Failed", "Not Useful"];

export function hasExplicitRights(candidate: SceneCandidate) {
  return ["Public Domain", "Royalty-Free", "Original / User-Owned", "Licensed"].includes(candidate.rights_status);
}
