"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WeeklyData, WeekTick } from "@/hooks/use-trends";
import type {
  TrainingReadiness,
  HrvData,
  FitnessMetrics,
  SleepData,
  BodyComposition,
  StressData,
} from "@/types/garmin";

const Plot = dynamic(() => import("@/lib/plotly"), { ssr: false });

const LAYOUT_BASE: Record<string, unknown> = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", size: 11 },
  margin: { t: 10, r: 20, b: 70, l: 50 },
  xaxis: { showgrid: false, type: "category", tickangle: -45 },
  yaxis: { gridcolor: "rgba(148,163,184,0.15)" },
  height: 280,
};

/** Layout base for daily scatter charts using date axis */
const DAILY_LAYOUT_BASE: Record<string, unknown> = {
  ...LAYOUT_BASE,
  xaxis: {
    showgrid: false,
    type: "date",
    tickformat: "%b %-d",
    tickangle: -45,
    dtick: 7 * 86400000, // weekly ticks
  },
};

function sortByDate<T extends { calendar_date: string }>(data: T[]): T[] {
  return [...data].sort((a, b) => a.calendar_date.localeCompare(b.calendar_date));
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Build xaxis tick config + year annotations from WeekTick[] */
function buildTickConfig(ticks?: WeekTick[]) {
  if (!ticks || ticks.length === 0) return { xaxisOverride: {}, yearAnnotations: [] };

  // Drop last tick to avoid overlap with edge
  const useTicks = ticks.length >= 2 ? ticks.slice(0, -1) : ticks;
  const tickvals = useTicks.map((t) => t.label);
  const ticktext = useTicks.map((t) => t.label);

  // Group ticks by year, place annotation at center of each group
  const yearGroups = new Map<number, string[]>();
  for (const t of ticks) {
    const labels = yearGroups.get(t.year) ?? [];
    labels.push(t.label);
    yearGroups.set(t.year, labels);
  }

  const annotations: Record<string, unknown>[] = [];
  for (const [year, labels] of yearGroups) {
    const midLabel = labels[Math.floor(labels.length / 2)];
    annotations.push({
      x: midLabel,
      y: -0.32,
      xref: "x",
      yref: "paper",
      text: `<b>${year}</b>`,
      showarrow: false,
      font: { size: 10, color: "#64748b" },
    });
  }

  return {
    xaxisOverride: { tickmode: "array" as const, tickvals, ticktext },
    yearAnnotations: annotations,
  };
}

/** Compute linear regression trend line (returns y values for indices 0..n-1) */
function trendLine(yValues: (number | null)[]): number[] {
  const valid: { x: number; y: number }[] = [];
  yValues.forEach((v, i) => {
    if (v != null) valid.push({ x: i, y: v });
  });
  if (valid.length < 2) return [];

  const n = valid.length;
  const sumX = valid.reduce((s, p) => s + p.x, 0);
  const sumY = valid.reduce((s, p) => s + p.y, 0);
  const sumXY = valid.reduce((s, p) => s + p.x * p.y, 0);
  const sumX2 = valid.reduce((s, p) => s + p.x * p.x, 0);

  const denom = n * sumX2 - sumX * sumX;
  if (denom === 0) return [];

  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;

  return yValues.map((_, i) => slope * i + intercept);
}

const CONFIG = { displayModeBar: false, responsive: true } as const;
const STYLE = { width: "100%", height: "280px" };

function ChartCard({
  title,
  average,
  averageSuffix = "",
  children,
}: {
  title: string;
  average?: string;
  averageSuffix?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">
            {title}
          </CardTitle>
          {average && (
            <span className="text-base font-semibold">
              avg {average}{averageSuffix}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

// ── Weekly bar charts ──

export function WeeklyElevationChart({ data, average, weekTicks }: { data: WeeklyData[]; average?: number; weekTicks?: WeekTick[] }) {
  if (data.length === 0) return null;
  const { xaxisOverride, yearAnnotations } = buildTickConfig(weekTicks);
  return (
    <ChartCard title="Weekly elevation gain" average={average != null ? `${Math.round(average)} m` : undefined} averageSuffix="/wk">
      <Plot
        data={[
          {
            x: data.map((d) => d.weekLabel),
            y: data.map((d) => Math.round(d.elevationGain)),
            type: "bar" as const,
            marker: { color: "#FF8C00" },
            hovertemplate: "%{y} m elev.<extra></extra>",
          },
        ]}
        layout={{
          ...LAYOUT_BASE,
          xaxis: { ...LAYOUT_BASE.xaxis as object, ...xaxisOverride },
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Elev. (m)" } },
          annotations: yearAnnotations,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function WeeklyVolumeChart({ data, average, weekTicks }: { data: WeeklyData[]; average?: number; weekTicks?: WeekTick[] }) {
  if (data.length === 0) return null;
  const { xaxisOverride, yearAnnotations } = buildTickConfig(weekTicks);
  return (
    <ChartCard title="Weekly volume" average={average != null ? `${(average / 1000).toFixed(1)} km` : undefined} averageSuffix="/wk">
      <Plot
        data={[
          {
            x: data.map((d) => d.weekLabel),
            y: data.map((d) => +(d.distance / 1000).toFixed(1)),
            type: "bar" as const,
            marker: { color: "#0891B2" },
            hovertemplate: "%{y} km<extra></extra>",
          },
        ]}
        layout={{
          ...LAYOUT_BASE,
          xaxis: { ...LAYOUT_BASE.xaxis as object, ...xaxisOverride },
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Distance (km)" } },
          annotations: yearAnnotations,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

// ── Daily charts with trend lines ──

export function Vo2MaxChart({ data, startDate }: { data: FitnessMetrics[]; startDate?: string }) {
  const filtered = sortByDate(data.filter((d) => d.vo2_max_running != null));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.vo2_max_running ?? 0), 0) / filtered.length;
  const xDates = filtered.map((d) => d.calendar_date);
  const yValues = filtered.map((d) => d.vo2_max_running);
  const trend = trendLine(yValues);

  return (
    <ChartCard title="VO2 Max (running)" average={avg.toFixed(1)}>
      <Plot
        data={[
          {
            x: xDates,
            y: yValues,
            type: "scatter" as const,
            mode: "lines+markers" as const,
            line: { color: "#0EA5E9", width: 2 },
            marker: { size: 4 },
            hovertemplate: "%{x|%b %-d}: %{y:.1f}<extra></extra>",
          },
          ...(trend.length > 0
            ? [
                {
                  x: xDates,
                  y: trend,
                  type: "scatter" as const,
                  mode: "lines" as const,
                  line: { color: "#0EA5E9", width: 1, dash: "dash" as const },
                  hoverinfo: "skip" as const,
                  showlegend: false,
                },
              ]
            : []),
        ]}
        layout={{
          ...DAILY_LAYOUT_BASE,
          xaxis: { ...DAILY_LAYOUT_BASE.xaxis as object, range: [startDate, todayISO()] },
          yaxis: { ...DAILY_LAYOUT_BASE.yaxis as object, title: { text: "VO2 Max" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function HrvChart({ data, startDate }: { data: HrvData[]; startDate?: string }) {
  const filtered = sortByDate(data.filter(
    (d) => d.weekly_avg != null || d.last_night_avg != null
  ));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.weekly_avg ?? d.last_night_avg ?? 0), 0) / filtered.length;
  const xDates = filtered.map((d) => d.calendar_date);
  const yValues = filtered.map((d) => d.weekly_avg ?? d.last_night_avg);
  const trend = trendLine(yValues);

  return (
    <ChartCard title="HRV" average={`${Math.round(avg)} ms`}>
      <Plot
        data={[
          {
            x: xDates,
            y: yValues,
            type: "scatter" as const,
            mode: "lines" as const,
            line: { color: "#10B981", width: 2 },
            hovertemplate: "%{x|%b %-d}: %{y:.0f} ms<extra></extra>",
          },
          ...(trend.length > 0
            ? [
                {
                  x: xDates,
                  y: trend,
                  type: "scatter" as const,
                  mode: "lines" as const,
                  line: { color: "#10B981", width: 1, dash: "dash" as const },
                  hoverinfo: "skip" as const,
                  showlegend: false,
                },
              ]
            : []),
        ]}
        layout={{
          ...DAILY_LAYOUT_BASE,
          xaxis: { ...DAILY_LAYOUT_BASE.xaxis as object, range: [startDate, todayISO()] },
          yaxis: { ...DAILY_LAYOUT_BASE.yaxis as object, title: { text: "HRV (ms)" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function TrainingLoadChart({ data, startDate }: { data: TrainingReadiness[]; startDate?: string }) {
  const filtered = sortByDate(data.filter((d) => d.acute_load != null));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.acute_load ?? 0), 0) / filtered.length;
  const xDates = filtered.map((d) => d.calendar_date);
  const yValues = filtered.map((d) => d.acute_load);
  const trend = trendLine(yValues);

  return (
    <ChartCard title="Training load" average={Math.round(avg).toString()}>
      <Plot
        data={[
          {
            x: xDates,
            y: yValues,
            type: "scatter" as const,
            mode: "lines" as const,
            line: { color: "#ef4444", width: 2 },
            hovertemplate: "%{x|%b %-d}: %{y:.0f}<extra></extra>",
          },
          ...(trend.length > 0
            ? [
                {
                  x: xDates,
                  y: trend,
                  type: "scatter" as const,
                  mode: "lines" as const,
                  line: { color: "#ef4444", width: 1, dash: "dash" as const },
                  hoverinfo: "skip" as const,
                  showlegend: false,
                },
              ]
            : []),
        ]}
        layout={{
          ...DAILY_LAYOUT_BASE,
          xaxis: { ...DAILY_LAYOUT_BASE.xaxis as object, range: [startDate, todayISO()] },
          yaxis: { ...DAILY_LAYOUT_BASE.yaxis as object, title: { text: "Load" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function SleepScoreChart({ data, startDate }: { data: SleepData[]; startDate?: string }) {
  const filtered = sortByDate(data.filter((d) => d.sleep_score != null));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.sleep_score ?? 0), 0) / filtered.length;
  const xDates = filtered.map((d) => d.calendar_date);
  const yValues = filtered.map((d) => d.sleep_score);
  const trend = trendLine(yValues);

  return (
    <ChartCard title="Sleep score" average={Math.round(avg).toString()}>
      <Plot
        data={[
          {
            x: xDates,
            y: yValues,
            type: "scatter" as const,
            mode: "lines+markers" as const,
            line: { color: "#8B5CF6", width: 2 },
            marker: { size: 3 },
            hovertemplate: "%{x|%b %-d}: %{y:.0f}<extra></extra>",
          },
          ...(trend.length > 0
            ? [
                {
                  x: xDates,
                  y: trend,
                  type: "scatter" as const,
                  mode: "lines" as const,
                  line: { color: "#8B5CF6", width: 1, dash: "dash" as const },
                  hoverinfo: "skip" as const,
                  showlegend: false,
                },
              ]
            : []),
        ]}
        layout={{
          ...DAILY_LAYOUT_BASE,
          xaxis: { ...DAILY_LAYOUT_BASE.xaxis as object, range: [startDate, todayISO()] },
          yaxis: { ...DAILY_LAYOUT_BASE.yaxis as object, title: { text: "Score" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function WeightChart({ data, startDate }: { data: BodyComposition[]; startDate?: string }) {
  const filtered = [...data]
    .filter((d) => d.weight_kg != null)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.weight_kg ?? 0), 0) / filtered.length;
  const xDates = filtered.map((d) => d.timestamp.slice(0, 10));
  const yValues = filtered.map((d) => d.weight_kg);
  const trend = trendLine(yValues);

  return (
    <ChartCard title="Weight" average={`${avg.toFixed(1)} kg`}>
      <Plot
        data={[
          {
            x: xDates,
            y: yValues,
            type: "scatter" as const,
            mode: "lines+markers" as const,
            line: { color: "#F59E0B", width: 2 },
            marker: { size: 4 },
            hovertemplate: "%{x|%b %-d}: %{y:.1f} kg<extra></extra>",
          },
          ...(trend.length > 0
            ? [
                {
                  x: xDates,
                  y: trend,
                  type: "scatter" as const,
                  mode: "lines" as const,
                  line: { color: "#F59E0B", width: 1, dash: "dash" as const },
                  hoverinfo: "skip" as const,
                  showlegend: false,
                },
              ]
            : []),
        ]}
        layout={{
          ...DAILY_LAYOUT_BASE,
          xaxis: { ...DAILY_LAYOUT_BASE.xaxis as object, range: [startDate, todayISO()] },
          yaxis: { ...DAILY_LAYOUT_BASE.yaxis as object, title: { text: "kg" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function StressChart({ data, startDate }: { data: StressData[]; startDate?: string }) {
  const filtered = sortByDate(data.filter((d) => d.average_stress_level != null));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.average_stress_level ?? 0), 0) / filtered.length;
  const xDates = filtered.map((d) => d.calendar_date);
  const yValues = filtered.map((d) => d.average_stress_level);
  const trend = trendLine(yValues);

  return (
    <ChartCard title="Stress level" average={Math.round(avg).toString()}>
      <Plot
        data={[
          {
            x: xDates,
            y: yValues,
            type: "scatter" as const,
            mode: "lines" as const,
            line: { color: "#EC4899", width: 2 },
            hovertemplate: "%{x|%b %-d}: %{y:.0f}<extra></extra>",
          },
          ...(trend.length > 0
            ? [
                {
                  x: xDates,
                  y: trend,
                  type: "scatter" as const,
                  mode: "lines" as const,
                  line: { color: "#EC4899", width: 1, dash: "dash" as const },
                  hoverinfo: "skip" as const,
                  showlegend: false,
                },
              ]
            : []),
        ]}
        layout={{
          ...DAILY_LAYOUT_BASE,
          xaxis: { ...DAILY_LAYOUT_BASE.xaxis as object, range: [startDate, todayISO()] },
          yaxis: { ...DAILY_LAYOUT_BASE.yaxis as object, title: { text: "Stress" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}
