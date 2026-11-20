import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSavedTrials } from "./useSavedTrials";
import { toast } from "sonner";
import { apiClient } from "../lib/apiClient";
import { CLINICAL } from "../lib/api";
import { useAuthContext } from "../contexts/AuthContext";
import { useErrorHandler } from "./useErrorHandler";

export function useSaveTrial() {
  const queryClient = useQueryClient();
  const { savedTrialIds } = useSavedTrials();
  const { isAuthenticated, openAuthModal } = useAuthContext();
  const { handleError } = useErrorHandler();

  const mutation = useMutation({
    mutationFn: async ({
      trialId,
      isSaved,
    }: {
      trialId: string;
      isSaved: boolean;
    }) => {
      if (isSaved) {
        try {
          await apiClient.delete(CLINICAL.SAVE_TRIAL(trialId));
        } catch (err: any) {
          if (err?.response?.status === 404) {
            return { trialId, saved: false };
          }
          throw err;
        }
        return { trialId, saved: false };
      } else {
        await apiClient.post(CLINICAL.SAVE_TRIAL(trialId), { notes: null }); // ← add body
        return { trialId, saved: true };
      }
    },

    onMutate: async ({ trialId, isSaved }) => {
      // Cancel in-flight queries that could overwrite our optimistic update
      await queryClient.cancelQueries({ queryKey: ["savedTrials"] });
      await queryClient.cancelQueries({ queryKey: ["trials"] });
      await queryClient.cancelQueries({ queryKey: ["trial", trialId] });

      // Snapshot previous state for rollback
      const previousSavedTrials = queryClient.getQueryData<string[]>([
        "savedTrials",
      ]);

      // Optimistically update the savedTrials cache
      queryClient.setQueryData<string[]>(["savedTrials"], (old = []) => {
        return isSaved
          ? old.filter((id) => id !== trialId) // remove if unsaving
          : [...old, trialId]; // add if saving
      });

      return { previousSavedTrials };
    },

    onSuccess: ({ saved }) => {
      if (saved) {
        toast.success("Trial Saved", {
          description: "Added to your saved trials list.",
        });
      } else {
        toast("Trial Removed", {
          description: "Removed from your saved trials list.",
        });
      }
    },

    onError: (err, _variables, context) => {
      // Restore previous cache
      if (context?.previousSavedTrials) {
        queryClient.setQueryData(["savedTrials"], context.previousSavedTrials);
      }

      handleError(err, "Could not update your saved trials. Please try again.");
    },

    onSettled: (_data, _err, { trialId }) => {
      queryClient.invalidateQueries({ queryKey: ["savedTrials"] });
      queryClient.invalidateQueries({ queryKey: ["trial", trialId] });
    },
  });

  const toggleSave = (trialId: string) => {
    if (!isAuthenticated) {
      openAuthModal("Sign in to your Voche account to save clinical trials.");
      return;
    }
    const isSaved = savedTrialIds.includes(trialId);
    mutation.mutate({ trialId, isSaved });
  };

  const isSaved = (trialId: string) => savedTrialIds.includes(trialId);

  return { toggleSave, isSaved, isPending: mutation.isPending };
}

