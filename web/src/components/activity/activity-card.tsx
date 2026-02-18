"use client";

import Link from "next/link";
import { Mountain, Clock, Heart, Route } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Activity } from "@/types/garmin";
import {
  formatDate,
  formatDuration,
  formatDistance,
  formatElevation,
  formatPace,
  activityTypeLabel,
} from "@/lib/utils";

export function ActivityCard({ activity }: { activity: Activity }) {
  return (
    <Link href={`/activity/${activity.activity_id}`}>
      <Card className="transition-colors hover:bg-accent/50">
        <CardContent className="flex items-center gap-4 py-3">
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">
                {activity.activity_name ?? "Activity"}
              </span>
              <Badge variant="secondary" className="text-xs shrink-0">
                {activityTypeLabel(activity.activity_type)}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              {formatDate(activity.start_timestamp)}
            </p>
          </div>

          <div className="hidden sm:flex items-center gap-4 text-sm text-muted-foreground shrink-0">
            {activity.elevation_gain_meters != null && activity.elevation_gain_meters > 0 && (
              <span className="flex items-center gap-1">
                <Mountain className="h-3.5 w-3.5" />
                {formatElevation(activity.elevation_gain_meters)}
              </span>
            )}
            {activity.distance_meters != null && activity.distance_meters > 0 && (
              <span className="flex items-center gap-1">
                <Route className="h-3.5 w-3.5" />
                {formatDistance(activity.distance_meters)}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5" />
              {formatDuration(activity.duration_seconds)}
            </span>
            {activity.average_speed != null && activity.average_speed > 0 && activity.distance_meters != null && activity.distance_meters > 0 && (
              <span className="text-xs">
                {formatPace(activity.average_speed)}
              </span>
            )}
            {activity.average_hr != null && (
              <span className="flex items-center gap-1">
                <Heart className="h-3.5 w-3.5" />
                {activity.average_hr} bpm
              </span>
            )}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
