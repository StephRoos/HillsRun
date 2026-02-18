"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { WeeklyData } from "@/hooks/use-trends";
import type { TrainingReadiness, HrvData, FitnessMetrics } from "@/types/garmin";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const LAYOUT_BASE: Record<string, unknown> = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", size: 11 },
  margin: { t: 10, r: 20, b: 40, l: 50 },
  xaxis: { showgrid: false, type: "category", tickangle: -45 },
  yaxis: { gridcolor: "rgba(148,163,184,0.15)" },
  height: 280,
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { day: "numeric", month: "short" });
}

function sortByDate<T extends { calendar_date: string }>(data: T[]): T[] {
  return [...data].sort((a, b) => a.calendar_date.localeCompare(b.calendar_date));
}

const CONFIG = { displayModeBar: false, responsive: true } as const;
const STYLE = { width: "100%", height: "280px" };

function ChartCard({
  title,
  average,
  children,
}: {
  title: string;
  average?: string;
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
              avg {average}/wk
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function WeeklyElevationChart({ data, average }: { data: WeeklyData[]; average?: number }) {
  if (data.length === 0) return null;
  return (
    <ChartCard title="Weekly elevation gain" average={average != null ? `${Math.round(average)} m` : undefined}>
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
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Elev. (m)" } },
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function WeeklyVolumeChart({ data, average }: { data: WeeklyData[]; average?: number }) {
  if (data.length === 0) return null;
  return (
    <ChartCard title="Weekly volume" average={average != null ? `${(average / 1000).toFixed(1)} km` : undefined}>
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
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Distance (km)" } },
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function Vo2MaxChart({ data }: { data: FitnessMetrics[] }) {
  const filtered = sortByDate(data.filter((d) => d.vo2_max_running != null));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.vo2_max_running ?? 0), 0) / filtered.length;

  return (
    <ChartCard title="VO2 Max (running)" average={avg.toFixed(1)}>
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.vo2_max_running),
            type: "scatter" as const,
            mode: "lines+markers" as const,
            line: { color: "#0EA5E9", width: 2 },
            marker: { size: 4 },
            hovertemplate: "%{y:.1f}<extra></extra>",
          },
        ]}
        layout={{
          ...LAYOUT_BASE,
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "VO2 Max" } },
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function HrvChart({ data }: { data: HrvData[] }) {
  const filtered = sortByDate(data.filter(
    (d) => d.weekly_avg != null || d.last_night_avg != null
  ));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.weekly_avg ?? d.last_night_avg ?? 0), 0) / filtered.length;

  return (
    <ChartCard title="HRV" average={`${Math.round(avg)} ms`}>
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.weekly_avg ?? d.last_night_avg),
            type: "scatter" as const,
            mode: "lines" as const,
            name: "Weekly avg",
            line: { color: "#10B981", width: 2 },
            hovertemplate: "%{y:.0f} ms<extra></extra>",
          },
        ]}
        layout={{
          ...LAYOUT_BASE,
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "HRV (ms)" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function TrainingLoadChart({ data }: { data: TrainingReadiness[] }) {
  const filtered = sortByDate(data.filter((d) => d.acute_load != null));
  if (filtered.length === 0) return null;

  const avg = filtered.reduce((s, d) => s + (d.acute_load ?? 0), 0) / filtered.length;

  return (
    <ChartCard title="Training load" average={Math.round(avg).toString()}>
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.acute_load),
            type: "scatter" as const,
            mode: "lines" as const,
            line: { color: "#ef4444", width: 2 },
            hovertemplate: "%{y:.0f}<extra></extra>",
          },
        ]}
        layout={{
          ...LAYOUT_BASE,
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Load" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}
