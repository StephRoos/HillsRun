"use client";

import dynamic from "next/dynamic";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ActivitySplit } from "@/types/garmin";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const CHART_LAYOUT = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", size: 11 },
  margin: { t: 10, r: 20, b: 40, l: 50 },
  xaxis: { showgrid: false },
  yaxis: { gridcolor: "rgba(148,163,184,0.15)" },
} as const;

const CHART_CONFIG = { displayModeBar: false, responsive: true } as const;

export function SplitsElevationChart({ splits }: { splits: ActivitySplit[] }) {
  if (splits.length === 0) return null;

  const labels = splits.map((_, i) => `Split ${i + 1}`);
  const elevations = splits.map((s) => s.elevation_gain ?? 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          D+ par split
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Plot
          data={[
            {
              x: labels,
              y: elevations,
              type: "bar" as const,
              marker: { color: "#FF8C00" },
              hovertemplate: "%{y:.0f} m<extra></extra>",
            },
          ]}
          layout={{
            ...CHART_LAYOUT,
            height: 250,
            yaxis: { ...CHART_LAYOUT.yaxis, title: { text: "D+ (m)" } },
          }}
          config={CHART_CONFIG}
          style={{ width: "100%", height: "250px" }}
        />
      </CardContent>
    </Card>
  );
}

export function SplitsPaceChart({ splits }: { splits: ActivitySplit[] }) {
  if (splits.length === 0) return null;

  const labels = splits.map((_, i) => `Split ${i + 1}`);
  const paces = splits.map((s) => {
    if (!s.average_speed || s.average_speed <= 0) return 0;
    return 1000 / s.average_speed / 60; // min/km
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          Allure par split
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Plot
          data={[
            {
              x: labels,
              y: paces,
              type: "bar" as const,
              marker: { color: "#0891B2" },
              hovertemplate: "%{y:.1f} min/km<extra></extra>",
            },
          ]}
          layout={{
            ...CHART_LAYOUT,
            height: 250,
            yaxis: {
              ...CHART_LAYOUT.yaxis,
              title: { text: "Allure (min/km)" },
              autorange: "reversed" as const,
            },
          }}
          config={CHART_CONFIG}
          style={{ width: "100%", height: "250px" }}
        />
      </CardContent>
    </Card>
  );
}

export function SplitsHrChart({ splits }: { splits: ActivitySplit[] }) {
  if (splits.length === 0) return null;

  const hasFcData = splits.some((s) => s.average_hr != null);
  if (!hasFcData) return null;

  const labels = splits.map((_, i) => `Split ${i + 1}`);
  const hrs = splits.map((s) => s.average_hr ?? 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          FC moy par split
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Plot
          data={[
            {
              x: labels,
              y: hrs,
              type: "scatter" as const,
              mode: "lines+markers" as const,
              line: { color: "#ef4444", width: 2 },
              marker: { size: 6 },
              hovertemplate: "%{y} bpm<extra></extra>",
            },
          ]}
          layout={{
            ...CHART_LAYOUT,
            height: 250,
            yaxis: { ...CHART_LAYOUT.yaxis, title: { text: "FC (bpm)" } },
          }}
          config={CHART_CONFIG}
          style={{ width: "100%", height: "250px" }}
        />
      </CardContent>
    </Card>
  );
}
