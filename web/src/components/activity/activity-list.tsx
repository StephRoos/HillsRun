"use client";

import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useActivities } from "@/hooks/use-activities";
import { ActivityCard } from "./activity-card";

const FILTERS = [
  { label: "Toutes", value: undefined },
  { label: "Running", value: "running" },
  { label: "Trail", value: "trail_running" },
  { label: "Muscu", value: "strength_training" },
] as const;

export function ActivityList() {
  const [filter, setFilter] = useState<string | undefined>(undefined);

  const { data, isPending, isError } = useActivities({
    limit: 20,
    activity_type: filter,
  });

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Recent activities</h2>
        <div className="flex gap-1">
          {FILTERS.map((f) => (
            <Button
              key={f.label}
              variant={filter === f.value ? "default" : "ghost"}
              size="sm"
              className="text-xs"
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </Button>
          ))}
        </div>
      </div>

      {isPending && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-sm text-destructive">
          Error loading activities.
        </p>
      )}

      {data && data.data.length === 0 && (
        <p className="text-sm text-muted-foreground py-8 text-center">
          No activities found.
        </p>
      )}

      {data && data.data.length > 0 && (
        <div className="space-y-2">
          {data.data.map((activity) => (
            <ActivityCard key={activity.activity_id} activity={activity} />
          ))}
        </div>
      )}
    </div>
  );
}
