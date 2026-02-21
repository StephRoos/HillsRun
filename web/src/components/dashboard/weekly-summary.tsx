"use client";

import { useMemo } from "react";
import { Mountain, Route, Clock, Activity as ActivityIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DeltaBadge } from "@/components/ui/delta-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useActivities } from "@/hooks/use-activities";
import { formatDuration, formatDistance, formatElevation } from "@/lib/utils";

const RUNNING_TYPES = new Set(["running", "trail_running"]);

function getMonday(weeksAgo: number) {
  const today = new Date();
  const monday = new Date(today);
  monday.setDate(today.getDate() - today.getDay() + (today.getDay() === 0 ? -6 : 1));
  monday.setDate(monday.getDate() - weeksAgo * 7);
  return monday;
}

function computeStats(activities: Array<{ start_timestamp?: string | null; activity_type?: string | null; duration_seconds?: number | null; distance_meters?: number | null; elevation_gain_meters?: number | null }>, startDate: string, endDate: string) {
  const weekActivities = activities.filter((a) => {
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
}

export function WeeklySummary() {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);

  // Current week: monday → today
  const currentMonday = getMonday(0);
  const currentStart = currentMonday.toISOString().slice(0, 10);

  // Previous week same window: prev monday → prev monday + same day offset
  const prevMonday = getMonday(1);
  const dayOffset = Math.floor((today.getTime() - currentMonday.getTime()) / 86400000);
  const prevEnd = new Date(prevMonday);
  prevEnd.setDate(prevMonday.getDate() + dayOffset);
  const prevStart = prevMonday.toISOString().slice(0, 10);
  const prevEndStr = prevEnd.toISOString().slice(0, 10);

  const { data, isPending, isError } = useActivities({
    start_date: prevStart,
    limit: 100,
  });

  const currentStats = useMemo(() => {
    if (!data?.data) return null;
    return computeStats(data.data, currentStart, todayStr);
  }, [data, currentStart, todayStr]);

  const prevStats = useMemo(() => {
    if (!data?.data) return null;
    return computeStats(data.data, prevStart, prevEndStr);
  }, [data, prevStart, prevEndStr]);

  if (isError) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">This week runs</h2>
        <p className="text-sm text-muted-foreground">Could not load data</p>
      </div>
    );
  }

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
    { label: "Runs", value: String(currentStats?.count ?? 0), icon: ActivityIcon, current: currentStats?.count ?? 0, previous: prevStats?.count ?? 0 },
    { label: "Distance", value: formatDistance(currentStats?.totalDistance ?? 0), icon: Route, current: currentStats?.totalDistance ?? 0, previous: prevStats?.totalDistance ?? 0 },
    { label: "Elevation", value: formatElevation(currentStats?.totalElevation ?? 0), icon: Mountain, current: currentStats?.totalElevation ?? 0, previous: prevStats?.totalElevation ?? 0 },
    { label: "Time", value: formatDuration(currentStats?.totalDuration ?? 0), icon: Clock, current: currentStats?.totalDuration ?? 0, previous: prevStats?.totalDuration ?? 0 },
  ];

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">This week runs <span className="text-sm font-normal text-muted-foreground">vs same days last week</span></h2>
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
            <DeltaBadge current={item.current} previous={item.previous} />
          </CardContent>
        </Card>
      ))}
      </div>
    </div>
  );
}
