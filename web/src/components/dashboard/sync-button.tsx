"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTriggerSync } from "@/hooks/use-sync";
import { toast } from "sonner";

export function SyncButton() {
  const { mutate: triggerSync, isPending } = useTriggerSync();

  function handleSync() {
    triggerSync(undefined, {
      onSuccess: () => toast.success("Sync started — data will refresh shortly"),
      onError: () => toast.error("Failed to trigger sync"),
    });
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={handleSync}
      disabled={isPending}
    >
      <RefreshCw className={`h-4 w-4 mr-2 ${isPending ? "animate-spin" : ""}`} />
      {isPending ? "Syncing..." : "Sync"}
    </Button>
  );
}
