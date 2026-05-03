import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useData } from "../contexts/DataContext";
import { toast } from "sonner";
import { apiClient } from "../lib/apiClient";
import { CLINICAL } from "../lib/api";

export function useSaveTrial() {
  const queryClient = useQueryClient();
  const { state, actions } = useData();

  const mutation = useMutation({
    mutationFn: async ({
      trialId,
      isSaved,
    }: {
      trialId: string;
      isSaved: boolean;
    }) => {
      if (isSaved) {
        await apiClient.delete(CLINICAL.SAVE_TRIAL(trialId));
        return { trialId, saved: false };
      } else {
        await apiClient.post(CLINICAL.SAVE_TRIAL(trialId));
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

      // Optimistically update DataContext
      if (isSaved) {
        actions.unsaveTrial(trialId);
      } else {
        actions.saveTrial(trialId);
      }

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

    onError: (_err, { trialId, isSaved }, context) => {
      // Restore previous cache
      if (context?.previousSavedTrials) {
        queryClient.setQueryData(["savedTrials"], context.previousSavedTrials);
      }

      // Rollback DataContext
      if (isSaved) {
        actions.saveTrial(trialId); // re-save since unsave failed
      } else {
        actions.unsaveTrial(trialId); // re-remove since save failed
      }

      toast.error("Something went wrong", {
        description: "Could not update your saved trials. Please try again.",
      });
    },

    onSettled: (_data, _err, { trialId }) => {
      queryClient.invalidateQueries({ queryKey: ["savedTrials"] });
      queryClient.invalidateQueries({ queryKey: ["trial", trialId] });
    },
  });

  const toggleSave = (trialId: string) => {
    const isSaved = state.savedTrials.includes(trialId);
    mutation.mutate({ trialId, isSaved });
  };

  const isSaved = (trialId: string) => state.savedTrials.includes(trialId);

  return { toggleSave, isSaved, isPending: mutation.isPending };
}
