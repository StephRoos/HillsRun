"use client";

import { Mountain, Route, Clock, Heart, Zap, ArrowDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ActivityDetail } from "@/types/garmin";
import { formatDuration, formatDistance, formatElevation, formatPace } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  icon: React.ElementType;
}

function MetricCard({ label, value, icon: Icon }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-xs font-medium">
          {label}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <p className="text-xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

export function ActivityMetrics({ activity }: { activity: ActivityDetail }) {
  const metrics = [
    {
      label: "D+",
      value: formatElevation(activity.elevation_gain_meters),
      icon: Mountain,
    },
    {
      label: "D-",
      value: formatElevation(activity.elevation_loss_meters),
      icon: ArrowDown,
    },
    {
      label: "Distance",
      value: formatDistance(activity.distance_meters),
      icon: Route,
    },
    {
      label: "Duration",
      value: formatDuration(activity.duration_seconds),
      icon: Clock,
    },
    {
      label: "Avg pace",
      value: formatPace(activity.average_speed),
      icon: Zap,
    },
    {
      label: "Avg / max HR",
      value:
        activity.average_hr != null
          ? `${activity.average_hr} / ${activity.max_hr ?? "—"} bpm`
          : "—",
      icon: Heart,
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {metrics.map((m) => (
        <MetricCard key={m.label} {...m} />
      ))}
    </div>
  );
}
