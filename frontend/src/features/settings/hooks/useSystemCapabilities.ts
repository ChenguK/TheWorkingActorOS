import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { systemCapabilitiesKey, useSystemCapabilities as useSharedSystemCapabilities } from "../../../services/system";
import { recalculateTravelExceptions } from "../api";

export function useSystemCapabilities() {
  const query = useSharedSystemCapabilities();
  const client = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const travel = useMutation({
    mutationFn: recalculateTravelExceptions,
    onSuccess: async (result) => {
      setMessage(`Travel recalculated: ${result.visible ?? 0} visible, ${result.travel_exception ?? 0} travel exceptions, ${result.needs_audition_location ?? 0} need audition location.`);
      await client.invalidateQueries({ queryKey: systemCapabilitiesKey });
    }
  });
  return { capabilities: query.data ?? null, loading: query.isLoading, error: query.error, message, recalculateTravel: travel.mutateAsync, mutationPending: travel.isPending, mutationError: travel.error };
}
