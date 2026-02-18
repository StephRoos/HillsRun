"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useActivities } from "@/hooks/use-activities";
import { formatDate, formatDistance, formatDuration, formatPace } from "@/lib/utils";
import type { ActivityDetail } from "@/types/garmin";

export function SimilarActivities({ activity }: { activity: ActivityDetail }) {
  const { data } = useActivities({ limit: 50, activity_type: activity.activity_type ?? undefined });

  if (!data?.data || !activity.distance_meters) return null;

  const distance = activity.distance_meters;
  const similar = data.data
    .filter(
      (a) =>
        a.activity_id !== activity.activity_id &&
        a.distance_meters != null &&
        Math.abs(a.distance_meters - distance) / distance <= 0.2
    )
    .slice(0, 5);

  if (similar.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          Similar activities
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-1">
        {similar.map((a) => (
          <Link
            key={a.activity_id}
            href={`/activity/${a.activity_id}`}
            className="flex items-center justify-between p-2 rounded-md hover:bg-accent/50 transition-colors text-sm"
          >
            <div className="min-w-0">
              <span className="font-medium truncate block">
                {a.custom_name ?? a.activity_name ?? "Activity"}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatDate(a.start_timestamp)}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
              <span>{formatDistance(a.distance_meters)}</span>
              <span>{formatDuration(a.duration_seconds)}</span>
              {a.average_speed ? <span>{formatPace(a.average_speed)}</span> : null}
            </div>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
