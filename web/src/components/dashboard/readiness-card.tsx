"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTrainingReadiness, useSleep, useBodyBattery, useHrv } from "@/hooks/use-metrics";

function ReadinessGauge({ score }: { score: number | null | undefined }) {
  const value = score ?? 0;
  const max = 100;
  const pct = Math.min(value / max, 1);

  // Arc from -135° to +135° (270° total sweep)
  const startAngle = -135;
  const sweep = 270;
  const endAngle = startAngle + sweep * pct;

  const r = 52;
  const cx = 64;
  const cy = 64;

  function polarToCartesian(angle: number) {
    const rad = (angle * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  }

  const start = polarToCartesian(startAngle);
  const end = polarToCartesian(endAngle);
  const largeArc = sweep * pct > 180 ? 1 : 0;

  const bgEnd = polarToCartesian(startAngle + sweep);
  const bgLargeArc = sweep > 180 ? 1 : 0;

  const color =
    value >= 70 ? "#10B981" : value >= 40 ? "#EAB308" : "#EF4444";

  return (
    <svg viewBox="0 0 128 128" className="w-32 h-32 mx-auto">
      {/* Background arc */}
      <path
        d={`M ${start.x} ${start.y} A ${r} ${r} 0 ${bgLargeArc} 1 ${bgEnd.x} ${bgEnd.y}`}
        fill="none"
        stroke="currentColor"
        className="text-muted/50"
        strokeWidth="8"
        strokeLinecap="round"
      />
      {/* Value arc */}
      {pct > 0 && (
        <path
          d={`M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
        />
      )}
      {/* Score text */}
      <text
        x={cx}
        y={cy + 4}
        textAnchor="middle"
        className="fill-foreground text-3xl font-bold"
        fontSize="28"
        fontWeight="bold"
      >
        {score ?? "—"}
      </text>
    </svg>
  );
}

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
          <Skeleton className="h-32 w-32 rounded-full mx-auto" />
          {Array.from({ length: 3 }).map((_, i) => (
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

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium">
          Today&apos;s readiness
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <ReadinessGauge score={readiness?.score} />
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
