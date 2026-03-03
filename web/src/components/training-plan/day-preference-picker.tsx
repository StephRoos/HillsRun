"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { DayPreferences } from "@/types/garmin";

const DAYS = [
  { num: 1, label: "Mon" },
  { num: 2, label: "Tue" },
  { num: 3, label: "Wed" },
  { num: 4, label: "Thu" },
  { num: 5, label: "Fri" },
  { num: 6, label: "Sat" },
  { num: 7, label: "Sun" },
];

// Interactive session rows: Long Run → Quality → Easy Run → Strength
const CATEGORIES = [
  { key: "long_run" as const, label: "Long Run", mode: "single" as const, color: "bg-orange-500/80 border-orange-500" },
  { key: "quality" as const, label: "Quality", mode: "multi" as const, maxSelect: 3, color: "bg-red-500/80 border-red-500" },
] as const;

interface DayPreferencePickerProps {
  value: DayPreferences;
  onChange: (prefs: DayPreferences) => void;
  /** Days the athlete can train (1-7). Non-available days are disabled. */
  availableDays?: number[];
  /** Max running sessions per week (from experience level). Enables EF day selection. */
  maxRunningSessions?: number;
}

/** Wrap day number: 7 + 1 → 1 (Sunday → Monday) */
function nextDay(d: number): number {
  return d === 7 ? 1 : d + 1;
}

function prevDay(d: number): number {
  return d === 1 ? 7 : d - 1;
}

/**
 * Compute days where hard sessions are blocked (constraint days).
 * - Day after long run → blocked
 * - Day after 2 consecutive quality sessions → blocked (3rd day rule)
 */
function getBlockedDays(prefs: DayPreferences): Set<number> {
  const blocked = new Set<number>();
  const quality = new Set(prefs.quality ?? []);

  if (prefs.long_run) {
    blocked.add(nextDay(prefs.long_run));
  }

  for (const q of quality) {
    if (quality.has(prevDay(q))) {
      blocked.add(nextDay(q));
    }
  }

  return blocked;
}

/** Get available days not already used by long_run or quality.
 *  When availableDays is not provided, all 7 days are considered available.
 */
function getEfCandidates(prefs: DayPreferences, availableDays: number[] | undefined): number[] {
  const allDays = availableDays ?? [1, 2, 3, 4, 5, 6, 7];
  const used = new Set<number>();
  if (prefs.long_run) used.add(prefs.long_run);
  for (const q of prefs.quality ?? []) used.add(q);
  return allDays.filter((d) => !used.has(d));
}

export function DayPreferencePicker({ value, onChange, availableDays, maxRunningSessions }: DayPreferencePickerProps) {
  const available = availableDays ? new Set(availableDays) : null;
  const blockedDays = useMemo(() => getBlockedDays(value), [value]);

  // EF logic: how many running session slots remain after long_run + quality
  const efCandidates = useMemo(() => getEfCandidates(value, availableDays), [value, availableDays]);
  const allocatedRunning = (value.long_run ? 1 : 0) + (value.quality?.length ?? 0);
  const remainingEfSlots = maxRunningSessions != null
    ? Math.max(0, maxRunningSessions - allocatedRunning)
    : efCandidates.length;
  const needsEfChoice = efCandidates.length > remainingEfSlots && remainingEfSlots > 0;

  // Auto-fill EF days when no choice needed
  const autoEfDays = useMemo(() => {
    if (needsEfChoice || remainingEfSlots === 0) return new Set<number>();
    return new Set(efCandidates.slice(0, remainingEfSlots));
  }, [needsEfChoice, remainingEfSlots, efCandidates]);

  // All EF days (user-selected or auto-filled) for the summary row
  const allEfDays = useMemo(() => {
    if (needsEfChoice) return new Set(value.easy_run ?? []);
    return autoEfDays;
  }, [needsEfChoice, value.easy_run, autoEfDays]);

  // Days with a running session (long_run, quality, or EF)
  const runningDays = useMemo(() => {
    const days = new Set<number>();
    if (value.long_run) days.add(value.long_run);
    for (const q of value.quality ?? []) days.add(q);
    for (const d of allEfDays) days.add(d);
    return days;
  }, [value.long_run, value.quality, allEfDays]);

  function handleClick(category: (typeof CATEGORIES)[number], dayNum: number) {
    if (available && !available.has(dayNum)) return;

    // Block placing long run or quality on blocked days (strength is OK — cross-training)
    if (category.key === "long_run" && blockedDays.has(dayNum)) return;
    if (category.key === "quality" && blockedDays.has(dayNum)) return;

    const next = { ...value };

    if (category.mode === "multi") {
      const key = category.key as "quality";
      const current = (value[key] as number[] | undefined) ?? [];
      if (current.includes(dayNum)) {
        const filtered = current.filter((d) => d !== dayNum);
        next[key] = filtered.length === 0 ? undefined : filtered;
      } else if (current.length < category.maxSelect) {
        next[key] = [...current, dayNum].sort((a, b) => a - b);
      }
    } else {
      const currentVal = value[category.key];
      (next as Record<string, unknown>)[category.key] = currentVal === dayNum ? undefined : dayNum;
    }

    // Clear quality days that became blocked
    const newBlocked = getBlockedDays(next);
    if (next.quality) {
      next.quality = next.quality.filter((d) => !newBlocked.has(d));
      if (next.quality.length === 0) next.quality = undefined;
    }

    // Clean up easy_run: remove days now used by long_run/quality, and trim to new slot count
    if (next.easy_run) {
      const newUsed = new Set<number>();
      if (next.long_run) newUsed.add(next.long_run);
      for (const q of next.quality ?? []) newUsed.add(q);
      next.easy_run = next.easy_run.filter((d) => !newUsed.has(d));
      const newAllocated = (next.long_run ? 1 : 0) + (next.quality?.length ?? 0);
      const newEfSlots = maxRunningSessions != null ? Math.max(0, maxRunningSessions - newAllocated) : next.easy_run.length;
      next.easy_run = next.easy_run.slice(0, newEfSlots);
      if (next.easy_run.length === 0) next.easy_run = undefined;
    }

    onChange(next);
  }

  function handleEfClick(dayNum: number) {
    if (!needsEfChoice) return;
    if (!efCandidates.includes(dayNum)) return;

    const next = { ...value };
    const current = value.easy_run ?? [];

    if (current.includes(dayNum)) {
      const filtered = current.filter((d) => d !== dayNum);
      next.easy_run = filtered.length === 0 ? undefined : filtered;
    } else if (current.length < remainingEfSlots) {
      next.easy_run = [...current, dayNum].sort((a, b) => a - b);
    }

    onChange(next);
  }

  function handleStrengthClick(dayNum: number) {
    if (available && !available.has(dayNum)) return;

    const next = { ...value };
    const current = value.strength ?? [];

    if (current.includes(dayNum)) {
      const filtered = current.filter((d) => d !== dayNum);
      next.strength = filtered.length === 0 ? undefined : filtered;
    } else if (current.length < 2) {
      next.strength = [...current, dayNum].sort((a, b) => a - b);
    }

    onChange(next);
  }

  const hasConflict = value.long_run && value.quality?.includes(value.long_run);
  const efSelected = new Set(value.easy_run ?? []);
  const strengthSelected = new Set(value.strength ?? []);
  const showEfRow = remainingEfSlots > 0 && efCandidates.length > 0;

  return (
    <div className="space-y-2">
      {/* Header row with day labels */}
      <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-1">
        <div />
        {DAYS.map((d) => (
          <div
            key={d.num}
            className={cn(
              "text-center text-xs font-medium py-1",
              available && !available.has(d.num) && "text-muted-foreground/40",
            )}
          >
            {d.label}
          </div>
        ))}
      </div>

      {/* Long Run + Quality rows */}
      {CATEGORIES.map((cat) => (
        <div key={cat.key} className="grid grid-cols-[100px_repeat(7,1fr)] gap-1">
          <div className="flex items-center text-xs font-medium">{cat.label}</div>
          {DAYS.map((d) => {
            const isUnavailable = available !== null && !available.has(d.num);
            const isBlocked = blockedDays.has(d.num);
            const isDisabled = isUnavailable || isBlocked;
            const isSelected =
              cat.mode === "multi"
                ? ((value[cat.key as "quality"] as number[] | undefined) ?? []).includes(d.num)
                : value[cat.key] === d.num;

            return (
              <button
                key={d.num}
                type="button"
                disabled={isDisabled}
                onClick={() => handleClick(cat, d.num)}
                className={cn(
                  "h-8 rounded-md border text-xs font-medium transition-colors",
                  isUnavailable && "opacity-25 cursor-not-allowed",
                  isBlocked && !isUnavailable && "opacity-40 cursor-not-allowed border-dashed",
                  !isDisabled && !isSelected && "border-border hover:border-muted-foreground/50 cursor-pointer",
                  isSelected && cat.color,
                  isSelected && "text-white",
                )}
              />
            );
          })}
        </div>
      ))}

      {/* Easy Run row — selectable when choice needed, auto-filled otherwise */}
      {showEfRow && (
        <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-1">
          <div className={cn(
            "flex items-center text-xs font-medium",
            needsEfChoice ? "text-foreground" : "text-muted-foreground",
          )}>
            Easy Run
          </div>
          {DAYS.map((d) => {
            const isCandidate = efCandidates.includes(d.num);
            const isAutoFilled = autoEfDays.has(d.num);
            const isUserSelected = efSelected.has(d.num);

            if (needsEfChoice) {
              return (
                <button
                  key={d.num}
                  type="button"
                  disabled={!isCandidate}
                  onClick={() => handleEfClick(d.num)}
                  className={cn(
                    "h-8 rounded-md border text-xs font-medium transition-colors",
                    !isCandidate && "opacity-25 cursor-not-allowed",
                    isCandidate && !isUserSelected && "border-border hover:border-blue-500/50 cursor-pointer",
                    isUserSelected && "bg-blue-500/80 border-blue-500 text-white",
                  )}
                />
              );
            }

            return (
              <div
                key={d.num}
                className={cn(
                  "h-8 rounded-md border border-dashed flex items-center justify-center text-[10px]",
                  isAutoFilled
                    ? "border-blue-500/50 bg-blue-500/10 text-blue-500"
                    : "border-transparent",
                )}
              >
                {isAutoFilled && "EF"}
              </div>
            );
          })}
        </div>
      )}

      {/* Strength row — allowed on any day (cross-training) */}
      <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-1">
        <div className="flex items-center text-xs font-medium">Strength</div>
        {DAYS.map((d) => {
          const isUnavailable = available !== null && !available.has(d.num);
          const isSelected = strengthSelected.has(d.num);

          return (
            <button
              key={d.num}
              type="button"
              disabled={isUnavailable}
              onClick={() => handleStrengthClick(d.num)}
              className={cn(
                "h-8 rounded-md border text-xs font-medium transition-colors",
                isUnavailable && "opacity-25 cursor-not-allowed",
                !isUnavailable && !isSelected && "border-border hover:border-muted-foreground/50 cursor-pointer",
                isSelected && "bg-cyan-500/80 border-cyan-500 text-white",
              )}
            />
          );
        })}
      </div>

      {/* Summary row: REC (easy run day) / REST (no session) */}
      <div className="grid grid-cols-[100px_repeat(7,1fr)] gap-1">
        <div className="flex items-center text-xs font-medium text-muted-foreground">Status</div>
        {DAYS.map((d) => {
          const isEf = allEfDays.has(d.num);
          const hasRunning = runningDays.has(d.num);
          const isUnavailable = available !== null && !available.has(d.num);
          // REST = no running session on this day (and day is potentially available)
          const isRest = !hasRunning && !isUnavailable;

          return (
            <div
              key={d.num}
              className={cn(
                "h-8 rounded-md border border-dashed flex items-center justify-center text-[10px]",
                isEf && "border-green-500/50 bg-green-500/10 text-green-500",
                isRest && "border-muted-foreground/30 bg-muted/10 text-muted-foreground",
                !isEf && !isRest && "border-transparent",
              )}
            >
              {isEf && "REC"}
              {isRest && "REST"}
            </div>
          );
        })}
      </div>

      {/* Conflict warning */}
      {hasConflict && (
        <p className="text-xs text-amber-500">
          Long run and quality share the same day — long run will take priority.
        </p>
      )}
    </div>
  );
}
