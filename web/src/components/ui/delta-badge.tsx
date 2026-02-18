interface DeltaBadgeProps {
  current: number;
  previous: number | null;
  mode?: "percent" | "absolute";
  higherIsBetter?: boolean;
}

export function DeltaBadge({
  current,
  previous,
  mode = "percent",
  higherIsBetter = true,
}: DeltaBadgeProps) {
  if (previous === null) return null;

  if (mode === "percent") {
    if (previous === 0 && current === 0)
      return <span className="text-xs text-muted-foreground">—</span>;
    if (previous === 0)
      return <span className="text-xs text-emerald-500">↑ new</span>;
    const pct = Math.round(((current - previous) / previous) * 100);
    if (pct === 0)
      return <span className="text-xs text-muted-foreground">—</span>;
    const isPositive = pct > 0;
    const isGood = higherIsBetter ? isPositive : !isPositive;
    const color = isGood ? "text-emerald-500" : "text-red-500";
    const arrow = isPositive ? "↑" : "↓";
    return (
      <span className={`text-xs ${color}`}>
        {arrow} {Math.abs(pct)}%
      </span>
    );
  }

  // absolute mode
  const diff = Math.round(current - previous);
  if (diff === 0)
    return <span className="text-xs text-muted-foreground">—</span>;
  const isPositive = diff > 0;
  const isGood = higherIsBetter ? isPositive : !isPositive;
  const color = isGood ? "text-emerald-500" : "text-red-500";
  const sign = isPositive ? "+" : "";
  return (
    <span className={`text-xs ${color}`}>
      {sign}{diff}
    </span>
  );
}
