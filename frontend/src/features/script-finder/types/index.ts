export type {
  CareerDevelopmentTask,
  MaterialCreationPlan,
  SceneCandidate,
  ScriptSource
} from "../../../types/domain";

export type ScriptSourceFormState = {
  name: string;
  url: string;
  source_type: string;
  rights_status: string;
  notes: string;
  approved: boolean;
};
