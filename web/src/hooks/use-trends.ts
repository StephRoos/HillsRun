import { useMemo } from "react";
import { useActivities } from "./use-activities";
import {
  useTrainingReadiness,
  useHrv,
  useFitnessMetrics,
  useSleep,
  useBodyComposition,
  useStress,
} from "./use-metrics";
import type { Activity } from "@/types/garmin";

export type Period = "4w" | "3m" | "6m" | "1y";

const RUNNING_TYPES = new Set(["running", "trail_running"]);

function periodToDays(period: Period): number {
  switch (period) {
    case "4w": return 28;
    case "3m": return 90;
    case "6m": return 180;
    case "1y": return 365;
  }
}

function periodToWeeks(period: Period): number {
  return Math.round(periodToDays(period) / 7);
}

function getStartDate(period: Period): string {
  const d = new Date();
  d.setDate(d.getDate() - periodToDays(period));
  return d.toISOString().slice(0, 10);
}

function getWeekMonday(dateStr: string): string {
  const d = new Date(dateStr);
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() - (dayNum - 1));
  return d.toISOString().slice(0, 10);
}

function formatWeekLabel(mondayStr: string): string {
  const d = new Date(mondayStr);
  return d.toLocaleDateString("en-US", { day: "numeric", month: "short" });
}

export interface WeekTick {
  label: string;     // e.g. "Nov 3"
  year: number;      // e.g. 2025
  isYearStart: boolean; // true on first tick and year boundaries
}

/** Generate all Monday ticks from startDate to today */
function generateAllWeekTicks(startDate: string): WeekTick[] {
  const ticks: WeekTick[] = [];
  const start = new Date(startDate);
  const dayNum = start.getUTCDay() || 7;
  start.setUTCDate(start.getUTCDate() - (dayNum - 1));
  const now = new Date();
  const cursor = new Date(start);
  let lastYear = -1;
  while (cursor <= now) {
    const year = cursor.getUTCFullYear();
    const label = formatWeekLabel(cursor.toISOString().slice(0, 10));
    ticks.push({ label, year, isYearStart: year !== lastYear });
    lastYear = year;
    cursor.setUTCDate(cursor.getUTCDate() + 7);
  }
  return ticks;
}

export interface WeeklyData {
  week: string;
  weekLabel: string;
  elevationGain: number;
  distance: number;
  duration: number;
  count: number;
}

export interface WeeklyAverages {
  elevationGain: number;
  distance: number;
  duration: number;
  count: number;
}

function aggregateWeekly(activities: Activity[]): WeeklyData[] {
  const weeks = new Map<string, WeeklyData>();

  for (const a of activities) {
    if (!a.start_timestamp) continue;
    const monday = getWeekMonday(a.start_timestamp);
    const existing = weeks.get(monday) ?? {
      week: monday,
      weekLabel: formatWeekLabel(monday),
      elevationGain: 0,
      distance: 0,
      duration: 0,
      count: 0,
    };
    existing.elevationGain += a.elevation_gain_meters ?? 0;
    existing.distance += a.distance_meters ?? 0;
    existing.duration += a.duration_seconds ?? 0;
    existing.count += 1;
    weeks.set(monday, existing);
  }

  return Array.from(weeks.values()).sort((a, b) => a.week.localeCompare(b.week));
}

function computeWeeklyAverages(weeklyData: WeeklyData[], numWeeks: number): WeeklyAverages {
  const weeks = numWeeks || weeklyData.length || 1;
  return {
    elevationGain: weeklyData.reduce((s, w) => s + w.elevationGain, 0) / weeks,
    distance: weeklyData.reduce((s, w) => s + w.distance, 0) / weeks,
    duration: weeklyData.reduce((s, w) => s + w.duration, 0) / weeks,
    count: weeklyData.reduce((s, w) => s + w.count, 0) / weeks,
  };
}

export function useTrends(period: Period) {
  const startDate = getStartDate(period);
  const numWeeks = periodToWeeks(period);
  const params = { start_date: startDate, limit: 200 };

  const activities = useActivities({ limit: 200, start_date: startDate });
  const readiness = useTrainingReadiness({ ...params });
  const hrv = useHrv({ ...params });
  const fitness = useFitnessMetrics({ ...params });
  const sleep = useSleep({ ...params });
  const weight = useBodyComposition({ ...params });
  const stress = useStress({ ...params });

  const filteredActivities = useMemo(() => {
    if (!activities.data?.data) return [];
    return activities.data.data.filter(
      (a) =>
        a.start_timestamp &&
        a.start_timestamp.slice(0, 10) >= startDate &&
        RUNNING_TYPES.has(a.activity_type ?? "")
    );
  }, [activities.data, startDate]);

  const weekTicks = useMemo(
    () => generateAllWeekTicks(startDate),
    [startDate]
  );

  const weeklyData = useMemo(
    () => aggregateWeekly(filteredActivities),
    [filteredActivities]
  );

  const weeklyAverages = useMemo(
    () => computeWeeklyAverages(weeklyData, numWeeks),
    [weeklyData, numWeeks]
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
    weeklyAverages,
    weekTicks,
    periodSummary,
    readiness: readiness.data?.data ?? [],
    hrv: hrv.data?.data ?? [],
    fitness: fitness.data?.data ?? [],
    sleep: sleep.data?.data ?? [],
    weight: weight.data?.data ?? [],
    stress: stress.data?.data ?? [],
    isPending:
      activities.isPending ||
      readiness.isPending ||
      hrv.isPending ||
      fitness.isPending ||
      sleep.isPending ||
      weight.isPending ||
      stress.isPending,
    isError:
      activities.isError &&
      readiness.isError &&
      hrv.isError &&
      fitness.isError &&
      sleep.isError &&
      weight.isError &&
      stress.isError,
  };
}
