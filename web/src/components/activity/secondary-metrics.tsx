"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ActivityDetail } from "@/types/garmin";

function Row({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

export function SecondaryMetrics({ activity }: { activity: ActivityDetail }) {
  const rows = [
    {
      label: "Cadence moy.",
      value: activity.average_running_cadence
        ? `${Math.round(activity.average_running_cadence)} spm`
        : null,
    },
    {
      label: "Oscillation verticale",
      value: activity.avg_vertical_oscillation
        ? `${activity.avg_vertical_oscillation.toFixed(1)} cm`
        : null,
    },
    {
      label: "Temps de contact sol",
      value: activity.avg_ground_contact_time
        ? `${Math.round(activity.avg_ground_contact_time)} ms`
        : null,
    },
    {
      label: "Stride length",
      value: activity.avg_stride_length
        ? `${(activity.avg_stride_length / 100).toFixed(2)} m`
        : null,
    },
    {
      label: "Puissance moy.",
      value: activity.average_power
        ? `${Math.round(activity.average_power)} W`
        : null,
    },
    {
      label: "Training Effect (aerobic)",
      value: activity.aerobic_training_effect
        ? `${activity.aerobic_training_effect.toFixed(1)}`
        : null,
    },
    {
      label: "Training Effect (anaerobic)",
      value: activity.anaerobic_training_effect
        ? `${activity.anaerobic_training_effect.toFixed(1)}`
        : null,
    },
    {
      label: "Estimated VO2max",
      value: activity.vo2_max_value
        ? `${activity.vo2_max_value.toFixed(1)}`
        : null,
    },
    {
      label: "Calories",
      value: activity.calories ? `${activity.calories} kcal` : null,
    },
    {
      label: "Altitude min / max",
      value:
        activity.min_elevation_meters != null && activity.max_elevation_meters != null
          ? `${Math.round(activity.min_elevation_meters)} / ${Math.round(activity.max_elevation_meters)} m`
          : null,
    },
    {
      label: "Temperature",
      value: activity.average_temperature
        ? `${activity.average_temperature.toFixed(1)}°C`
        : null,
    },
  ];

  const visibleRows = rows.filter((r) => r.value != null);

  if (visibleRows.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Detailed metrics
        </CardTitle>
      </CardHeader>
      <CardContent className="divide-y divide-border">
        {visibleRows.map((r) => (
          <Row key={r.label} label={r.label} value={r.value} />
        ))}
      </CardContent>
    </Card>
  );
}
