import { useQuery } from "@tanstack/react-query";
import { useAuthContext } from "../contexts/AuthContext";
import { apiClient } from "../lib/apiClient";
import { USERS } from "../lib/api";

/** Ids of the trials the logged-in user saved, from the server. */
export function useSavedTrials() {
  const { user } = useAuthContext();

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

  return { savedTrialIds: user ? savedTrialIds : [] };
}
