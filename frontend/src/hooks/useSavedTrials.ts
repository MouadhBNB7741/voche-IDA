import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useData } from "../contexts/DataContext";
import { useAuth } from "./useAuth";
import apiClient from "../services/axiosInterceptor";
import { USERS } from "../lib/api";

export function useSavedTrials() {
  const { user } = useAuth();
  const { actions } = useData();

  const { data: savedTrialIds = [] } = useQuery<string[]>({
    queryKey: ["savedTrials"],
    queryFn: async () => {
      const response = await apiClient.get(USERS.ME_SAVED_TRIALS);
      // Backend returns array of trial objects or IDs — extract IDs
      const data = response.data;
      return Array.isArray(data)
        ? data
            .map((t: { id?: string; trial_id?: string } | string) =>
              typeof t === "string" ? t : (t.id ?? t.trial_id ?? ""),
            )
            .filter(Boolean)
        : [];
    },
    enabled: !!user,
    staleTime: 30 * 1000,
    retry: false,
  });

  useEffect(() => {
    if (savedTrialIds.length > 0) {
      savedTrialIds.forEach((id) => actions.saveTrial(id));
    }
  }, [savedTrialIds]);

  return { savedTrialIds };
}
