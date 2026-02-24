"use client";

import { useState } from "react";
import { Mountain, Route, Clock, Activity as ActivityIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useTrends, type Period } from "@/hooks/use-trends";
import { formatDuration, formatDistance, formatElevation } from "@/lib/utils";
import {
  WeeklyElevationChart,
  WeeklyVolumeChart,
  Vo2MaxChart,
  HrvChart,
  TrainingLoadChart,
  SleepScoreChart,
  WeightChart,
  StressChart,
} from "@/components/charts/trend-charts";

const PERIODS: { label: string; value: Period }[] = [
  { label: "4w", value: "4w" },
  { label: "3m", value: "3m" },
  { label: "6m", value: "6m" },
  { label: "1y", value: "1y" },
];

export default function TrendsPage() {
  const [period, setPeriod] = useState<Period>("3m");
  const {
    weeklyData,
    weeklyAverages,
    weekTicks,
    startDate,
    periodSummary,
    readiness,
    hrv,
    fitness,
    sleep,
    weight,
    stress,
    isPending,
    isError,
  } = useTrends(period);

  if (isError) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Trends</h1>
        <p className="text-sm text-muted-foreground">Could not load trends data.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Trends</h1>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <Button
              key={p.value}
              variant={period === p.value ? "default" : "ghost"}
              size="sm"
              className="text-xs"
              onClick={() => setPeriod(p.value)}
            >
              {p.label}
            </Button>
          ))}
        </div>
      </div>

      {isPending ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-medium">
                Distance
              </CardTitle>
              <Route className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">
                {formatDistance(periodSummary.totalDistance)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-medium">
                Total elev.
              </CardTitle>
              <Mountain className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">
                {formatElevation(periodSummary.totalElevation)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-medium">
                Time
              </CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">
                {formatDuration(periodSummary.totalDuration)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-xs font-medium">
                Activities
              </CardTitle>
              <ActivityIcon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">{periodSummary.totalActivities}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {isPending ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-72" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <WeeklyVolumeChart data={weeklyData} average={weeklyAverages.distance} weekTicks={weekTicks} />
          <WeeklyElevationChart data={weeklyData} average={weeklyAverages.elevationGain} weekTicks={weekTicks} />
          <Vo2MaxChart data={fitness} startDate={startDate} />
          <HrvChart data={hrv} startDate={startDate} />
          <TrainingLoadChart data={readiness} startDate={startDate} />
          <SleepScoreChart data={sleep} startDate={startDate} />
          <WeightChart data={weight} startDate={startDate} />
          <StressChart data={stress} startDate={startDate} />
        </div>
      )}
    </div>
  );
}
