import { api } from "../api";
import type { SystemCapabilities } from "../../types/domain";

export function getSystemCapabilities() {
  return api.get<SystemCapabilities>("/system/capabilities");
}
