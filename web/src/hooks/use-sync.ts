import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";

export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync-status"],
    queryFn: () => garminApi.getSyncStatus(),
    refetchInterval: 30000,
  });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => garminApi.triggerSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sync-status"] });
      // Refresh dashboard data after a delay to let sync complete
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["activities"] });
        queryClient.invalidateQueries({ queryKey: ["training-readiness"] });
        queryClient.invalidateQueries({ queryKey: ["weekly-summary"] });
      }, 15000);
    },
  });
}
