"use client";

import { useMemo } from "react";
import { Mountain, Route, Clock, Activity as ActivityIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useActivities } from "@/hooks/use-activities";
import { formatDuration, formatDistance, formatElevation } from "@/lib/utils";

const RUNNING_TYPES = new Set(["running", "trail_running"]);

export function WeeklySummary() {
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1));
  const startDate = monday.toISOString().slice(0, 10);
  const endDate = today.toISOString().slice(0, 10);

  const { data, isPending } = useActivities({
    limit: 50,
  });

  const stats = useMemo(() => {
    if (!data?.data) return null;
    const weekActivities = data.data.filter((a) => {
      if (!a.start_timestamp) return false;
      const d = a.start_timestamp.slice(0, 10);
      return d >= startDate && d <= endDate;
    });

    const running = weekActivities.filter((a) => RUNNING_TYPES.has(a.activity_type ?? ""));

    return {
      count: running.length,
      totalDuration: running.reduce((s, a) => s + (a.duration_seconds ?? 0), 0),
      totalDistance: running.reduce((s, a) => s + (a.distance_meters ?? 0), 0),
      totalElevation: running.reduce((s, a) => s + (a.elevation_gain_meters ?? 0), 0),
    };
  }, [data, startDate, endDate]);

  if (isPending) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-16" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-7 w-20" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const items = [
    { label: "Distance", value: formatDistance(stats?.totalDistance ?? 0), icon: Route },
    { label: "Elevation", value: formatElevation(stats?.totalElevation ?? 0), icon: Mountain },
    { label: "Time", value: formatDuration(stats?.totalDuration ?? 0), icon: Clock },
    { label: "Runs", value: String(stats?.count ?? 0), icon: ActivityIcon },
  ];

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">This week running</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">
              {item.label}
            </CardTitle>
            <item.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{item.value}</p>
          </CardContent>
        </Card>
      ))}
      </div>
    </div>
  );
}
