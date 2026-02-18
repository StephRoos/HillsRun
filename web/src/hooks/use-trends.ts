import { useMemo } from "react";
import { useActivities } from "./use-activities";
import { useTrainingReadiness, useHrv, useFitnessMetrics } from "./use-metrics";
import type { Activity } from "@/types/garmin";

export type Period = "4w" | "3m" | "6m" | "1y";

function periodToDays(period: Period): number {
  switch (period) {
    case "4w": return 28;
    case "3m": return 90;
    case "6m": return 180;
    case "1y": return 365;
  }
}

function getStartDate(period: Period): string {
  const d = new Date();
  d.setDate(d.getDate() - periodToDays(period));
  return d.toISOString().slice(0, 10);
}

function getISOWeek(dateStr: string): string {
  const d = new Date(dateStr);
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${d.getUTCFullYear()}-W${weekNo.toString().padStart(2, "0")}`;
}

export interface WeeklyData {
  week: string;
  elevationGain: number;
  distance: number;
  duration: number;
  count: number;
}

function aggregateWeekly(activities: Activity[]): WeeklyData[] {
  const weeks = new Map<string, WeeklyData>();

  for (const a of activities) {
    if (!a.start_timestamp) continue;
    const week = getISOWeek(a.start_timestamp);
    const existing = weeks.get(week) ?? {
      week,
      elevationGain: 0,
      distance: 0,
      duration: 0,
      count: 0,
    };
    existing.elevationGain += a.elevation_gain_meters ?? 0;
    existing.distance += a.distance_meters ?? 0;
    existing.duration += a.duration_seconds ?? 0;
    existing.count += 1;
    weeks.set(week, existing);
  }

  return Array.from(weeks.values()).sort((a, b) => a.week.localeCompare(b.week));
}

export function useTrends(period: Period) {
  const startDate = getStartDate(period);
  const params = { start_date: startDate, limit: 200 };

  const activities = useActivities({ limit: 200 });
  const readiness = useTrainingReadiness({ ...params });
  const hrv = useHrv({ ...params });
  const fitness = useFitnessMetrics({ ...params });

  const filteredActivities = useMemo(() => {
    if (!activities.data?.data) return [];
    return activities.data.data.filter(
      (a) => a.start_timestamp && a.start_timestamp.slice(0, 10) >= startDate
    );
  }, [activities.data, startDate]);

  const weeklyData = useMemo(
    () => aggregateWeekly(filteredActivities),
    [filteredActivities]
  );

  const periodSummary = useMemo(() => {
    return {
      totalElevation: filteredActivities.reduce((s, a) => s + (a.elevation_gain_meters ?? 0), 0),
      totalDistance: filteredActivities.reduce((s, a) => s + (a.distance_meters ?? 0), 0),
      totalDuration: filteredActivities.reduce((s, a) => s + (a.duration_seconds ?? 0), 0),
      totalActivities: filteredActivities.length,
    };
  }, [filteredActivities]);

  return {
    weeklyData,
    periodSummary,
    readiness: readiness.data?.data ?? [],
    hrv: hrv.data?.data ?? [],
    fitness: fitness.data?.data ?? [],
    isPending: activities.isPending || readiness.isPending || hrv.isPending || fitness.isPending,
  };
}
