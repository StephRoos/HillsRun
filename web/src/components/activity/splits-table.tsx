"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ActivitySplit } from "@/types/garmin";
import { formatDuration, formatDistance, formatPace } from "@/lib/utils";

export function SplitsTable({ splits }: { splits: ActivitySplit[] }) {
  if (splits.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          Splits
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="py-2 text-left font-medium">#</th>
                <th className="py-2 text-right font-medium">Distance</th>
                <th className="py-2 text-right font-medium">Duration</th>
                <th className="py-2 text-right font-medium">Allure</th>
                <th className="py-2 text-right font-medium">D+</th>
                <th className="py-2 text-right font-medium">FC moy</th>
              </tr>
            </thead>
            <tbody>
              {splits.map((split, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-2">{(split.split_index ?? i) + 1}</td>
                  <td className="py-2 text-right">
                    {formatDistance(split.distance_meters)}
                  </td>
                  <td className="py-2 text-right">
                    {formatDuration(split.duration_seconds)}
                  </td>
                  <td className="py-2 text-right">
                    {formatPace(split.average_speed)}
                  </td>
                  <td className="py-2 text-right">
                    {split.elevation_gain != null
                      ? `${Math.round(split.elevation_gain)} m`
                      : "—"}
                  </td>
                  <td className="py-2 text-right">
                    {split.average_hr != null ? `${split.average_hr} bpm` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
