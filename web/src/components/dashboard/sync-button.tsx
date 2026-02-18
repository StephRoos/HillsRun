"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTriggerSync } from "@/hooks/use-sync";

export function SyncButton() {
  const { mutate: triggerSync, isPending, isSuccess } = useTriggerSync();

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => triggerSync()}
      disabled={isPending}
    >
      <RefreshCw className={`h-4 w-4 mr-2 ${isPending ? "animate-spin" : ""}`} />
      {isPending ? "Syncing..." : isSuccess ? "Sync started" : "Sync"}
    </Button>
  );
}
