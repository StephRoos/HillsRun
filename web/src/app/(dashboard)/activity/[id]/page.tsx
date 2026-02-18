"use client";

import { use } from "react";
import { useActivity, useActivitySplits } from "@/hooks/use-activities";
import { Skeleton } from "@/components/ui/skeleton";
import { ActivityHeader } from "@/components/activity/activity-header";
import { ActivityMetrics } from "@/components/activity/activity-metrics";
import { SecondaryMetrics } from "@/components/activity/secondary-metrics";
import { SplitsTable } from "@/components/activity/splits-table";
import {
  SplitsElevationChart,
  SplitsPaceChart,
  SplitsHrChart,
} from "@/components/charts/activity-summary-chart";

export default function ActivityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: activity, isPending, isError } = useActivity(id);
  const { data: splitsData } = useActivitySplits(id);

  if (isPending) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-6 w-32" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </div>
    );
  }

  if (isError || !activity) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <p className="text-muted-foreground">Activity not found.</p>
      </div>
    );
  }

  const splits = splitsData?.data ?? [];

  return (
    <div className="p-6 space-y-6">
      <ActivityHeader activity={activity} />
      <ActivityMetrics activity={activity} />

      {splits.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <SplitsElevationChart splits={splits} />
          <SplitsPaceChart splits={splits} />
        </div>
      )}

      {splits.length > 0 && <SplitsHrChart splits={splits} />}

      <SplitsTable splits={splits} />
      <SecondaryMetrics activity={activity} />
    </div>
  );
}
