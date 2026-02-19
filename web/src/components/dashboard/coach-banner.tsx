"use client";

import { useCoachContext } from "@/lib/coach-context";
import { setViewAsAthlete } from "@/lib/garmin-api";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export function CoachBanner() {
  const { isViewingAthlete, athleteName, setAthlete } = useCoachContext();

  if (!isViewingAthlete) return null;

  return (
    <div className="flex items-center justify-between bg-primary/10 px-4 py-2 text-sm">
      <span>
        Viewing <strong>{athleteName}</strong>&apos;s data
      </span>
      <Button
        variant="ghost"
        size="sm"
        className="h-7 gap-1 text-xs"
        onClick={() => {
          setAthlete(null, null);
          setViewAsAthlete(null);
        }}
      >
        <X className="h-3.5 w-3.5" />
        Back to my data
      </Button>
    </div>
  );
}
