"use client";

import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTriggerSync } from "@/hooks/use-sync";

export function SyncButton() {
  const { trigger, isSyncing } = useTriggerSync();

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => trigger()}
      disabled={isSyncing}
    >
      <RefreshCw className={`h-4 w-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
      {isSyncing ? "Syncing..." : "Sync"}
    </Button>
  );
}
