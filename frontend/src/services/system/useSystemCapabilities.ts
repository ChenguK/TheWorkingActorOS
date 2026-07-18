import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "../api/queryKeys";
import { queryStaleTimes } from "../api/queryPolicy";
import { getSystemCapabilities } from "./api";

export const systemCapabilitiesKey = queryKeys.system.capabilities;

export function useSystemCapabilities() {
  return useQuery({
    queryKey: systemCapabilitiesKey,
    queryFn: getSystemCapabilities,
    staleTime: queryStaleTimes.configuration,
    refetchOnMount: false,
    refetchOnReconnect: true
  });
}
