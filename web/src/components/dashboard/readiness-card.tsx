"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTrainingReadiness, useSleep, useBodyBattery, useHrv } from "@/hooks/use-metrics";

function MetricRow({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value ?? "—"}</span>
    </div>
  );
}

export function ReadinessCard() {
  const today = new Date().toISOString().slice(0, 10);
  const params = { start_date: today, limit: 1 };

  const { data: trData, isPending: trLoading } = useTrainingReadiness(params);
  const { data: sleepData, isPending: sleepLoading } = useSleep(params);
  const { data: bbData, isPending: bbLoading } = useBodyBattery(params);
  const { data: hrvData, isPending: hrvLoading } = useHrv(params);

  const isPending = trLoading || sleepLoading || bbLoading || hrvLoading;

  if (isPending) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-32" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-5 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  const readiness = trData?.data?.[0];
  const sleep = sleepData?.data?.[0];
  const bb = bbData?.data?.[0];
  const hrv = hrvData?.data?.[0];

  const score = readiness?.score;
  const scoreColor =
    score == null
      ? "text-muted-foreground"
      : score >= 70
        ? "text-emerald-500"
        : score >= 40
          ? "text-yellow-500"
          : "text-red-500";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Readiness du jour
        </CardTitle>
        <p className={`text-4xl font-bold ${scoreColor}`}>
          {score ?? "—"}
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        <MetricRow label="Sleep Score" value={sleep?.sleep_score ?? null} />
        <MetricRow
          label="Body Battery"
          value={bb?.highest_value ?? bb?.charged_value ?? null}
        />
        <MetricRow
          label="HRV"
          value={hrv?.weekly_avg ?? hrv?.last_night_avg ?? null}
        />
      </CardContent>
    </Card>
  );
}
