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
  xaxis: { showgrid: false, type: "category" },
  yaxis: { gridcolor: "rgba(148,163,184,0.15)" },
  height: 280,
};

const DATE_LAYOUT: Record<string, unknown> = {
  ...LAYOUT_BASE,
  xaxis: { showgrid: false, type: "category", tickangle: -45 },
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
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function WeeklyElevationChart({ data }: { data: WeeklyData[] }) {
  if (data.length === 0) return null;
  return (
    <ChartCard title="Weekly elevation gain">
      <Plot
        data={[
          {
            x: data.map((d) => d.weekLabel),
            y: data.map((d) => Math.round(d.elevationGain)),
            type: "bar" as const,
            marker: { color: "#22c55e" },
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

export function WeeklyVolumeChart({ data }: { data: WeeklyData[] }) {
  if (data.length === 0) return null;
  return (
    <ChartCard title="Weekly volume">
      <Plot
        data={[
          {
            x: data.map((d) => d.weekLabel),
            y: data.map((d) => +(d.distance / 1000).toFixed(1)),
            type: "bar" as const,
            marker: { color: "#3b82f6" },
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

  return (
    <ChartCard title="VO2 Max (running)">
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.vo2_max_running),
            type: "scatter" as const,
            mode: "lines+markers" as const,
            line: { color: "#8b5cf6", width: 2 },
            marker: { size: 4 },
            hovertemplate: "%{y:.1f}<extra></extra>",
          },
        ]}
        layout={{
          ...DATE_LAYOUT,
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

  return (
    <ChartCard title="HRV">
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.weekly_avg ?? d.last_night_avg),
            type: "scatter" as const,
            mode: "lines+markers" as const,
            name: "Weekly avg",
            line: { color: "#06b6d4", width: 2 },
            marker: { size: 4 },
            hovertemplate: "%{y:.0f} ms<extra></extra>",
          },
        ]}
        layout={{
          ...DATE_LAYOUT,
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "HRV (ms)" } },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function ReadinessChart({ data }: { data: TrainingReadiness[] }) {
  const filtered = sortByDate(data.filter((d) => d.score != null));
  if (filtered.length === 0) return null;

  return (
    <ChartCard title="Training Readiness">
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.score),
            type: "scatter" as const,
            mode: "lines+markers" as const,
            line: { color: "#f59e0b", width: 2 },
            marker: { size: 4 },
            fill: "tozeroy" as const,
            fillcolor: "rgba(245,158,11,0.1)",
            hovertemplate: "%{y}<extra></extra>",
          },
        ]}
        layout={{
          ...DATE_LAYOUT,
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Score" }, range: [0, 100] },
          showlegend: false,
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}

export function TrainingLoadChart({ data }: { data: TrainingReadiness[] }) {
  const filtered = sortByDate(data.filter(
    (d) => d.acute_load != null || d.chronic_load != null
  ));
  if (filtered.length === 0) return null;

  return (
    <ChartCard title="Training load">
      <Plot
        data={[
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.acute_load),
            type: "scatter" as const,
            mode: "lines" as const,
            name: "Acute load",
            line: { color: "#ef4444", width: 2 },
            hovertemplate: "%{y:.0f}<extra>Acute</extra>",
          },
          {
            x: filtered.map((d) => formatDate(d.calendar_date)),
            y: filtered.map((d) => d.chronic_load),
            type: "scatter" as const,
            mode: "lines" as const,
            name: "Chronic load",
            line: { color: "#22c55e", width: 2 },
            hovertemplate: "%{y:.0f}<extra>Chronic</extra>",
          },
        ]}
        layout={{
          ...DATE_LAYOUT,
          yaxis: { ...LAYOUT_BASE.yaxis as object, title: { text: "Load" } },
          legend: {
            orientation: "h" as const,
            y: -0.2,
            font: { size: 10, color: "#94a3b8" },
          },
        }}
        config={CONFIG}
        style={STYLE}
      />
    </ChartCard>
  );
}
