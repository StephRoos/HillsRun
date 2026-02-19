import { useState, useCallback, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";
import { toast } from "sonner";

export function useSyncStatus() {
  return useQuery({
    queryKey: ["sync-status"],
    queryFn: () => garminApi.getSyncStatus(),
    staleTime: 60_000,
  });
}

const POLL_INTERVAL = 3000;
const POLL_TIMEOUT = 600000; // 10 min

function invalidateAllData(queryClient: ReturnType<typeof useQueryClient>) {
  queryClient.invalidateQueries({ queryKey: ["activities"] });
  queryClient.invalidateQueries({ queryKey: ["training-readiness"] });
  queryClient.invalidateQueries({ queryKey: ["weekly-summary"] });
  queryClient.invalidateQueries({ queryKey: ["sync-status"] });
  queryClient.invalidateQueries({ queryKey: ["garmin-account"] });
  queryClient.invalidateQueries({ queryKey: ["hrv"] });
  queryClient.invalidateQueries({ queryKey: ["sleep"] });
  queryClient.invalidateQueries({ queryKey: ["body-battery"] });
  queryClient.invalidateQueries({ queryKey: ["stress"] });
  queryClient.invalidateQueries({ queryKey: ["fitness-metrics"] });
  queryClient.invalidateQueries({ queryKey: ["body-composition"] });
}

export function useTriggerSync() {
  const queryClient = useQueryClient();
  const [isSyncing, setIsSyncing] = useState(false);
  const abortRef = useRef(false);

  const trigger = useCallback(
    async (options?: { mode?: string; days_back?: number }) => {
      if (isSyncing) return;
      setIsSyncing(true);
      abortRef.current = false;

      try {
        const result = await garminApi.triggerSync(options);
        const jobId = result?.job_id;

        if (!jobId) {
          // 409 or no job_id — sync already running
          toast.info("Sync already in progress");
          setIsSyncing(false);
          return;
        }

        toast.success("Sync started");

        // Poll until job completes
        const start = Date.now();
        const poll = () => {
          if (abortRef.current || Date.now() - start > POLL_TIMEOUT) {
            setIsSyncing(false);
            return;
          }
          garminApi
            .getSyncJob(jobId)
            .then((job) => {
              if (job.status === "completed") {
                invalidateAllData(queryClient);
                toast.success("Sync complete — data refreshed");
                setIsSyncing(false);
              } else if (job.status === "failed") {
                toast.error(`Sync failed: ${job.error ?? "unknown error"}`);
                setIsSyncing(false);
              } else {
                setTimeout(poll, POLL_INTERVAL);
              }
            })
            .catch(() => {
              // Network error — retry
              setTimeout(poll, POLL_INTERVAL);
            });
        };
        setTimeout(poll, POLL_INTERVAL);
      } catch {
        toast.error("Failed to trigger sync");
        setIsSyncing(false);
      }
    },
    [isSyncing, queryClient]
  );

  const cancel = useCallback(() => {
    abortRef.current = true;
  }, []);

  return { trigger, isSyncing, cancel };
}
