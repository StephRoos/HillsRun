"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useActivities } from "@/hooks/use-activities";
import { formatDuration, formatDistance, activityTypeLabel } from "@/lib/utils";
import type { Activity } from "@/types/garmin";

const ACTIVITY_COLORS: Record<string, string> = {
  running: "#FF8C00",
  trail_running: "#FF6B00",
  hiking: "#10B981",
  cycling: "#0891B2",
  swimming: "#0EA5E9",
  strength_training: "#8B5CF6",
  yoga: "#EC4899",
  walking: "#6B7280",
};

function getColor(type: string | null): string {
  return ACTIVITY_COLORS[type ?? ""] ?? "#94A3B8";
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number): number {
  // Monday = 0, Sunday = 6
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

export function ActivityCalendar() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  // Fetch 2 months of activities to cover current month
  const startDate = new Date(year, month, 1).toISOString().slice(0, 10);
  const endDate = new Date(year, month + 1, 0).toISOString().slice(0, 10);

  const { data, isPending } = useActivities({
    limit: 100,
    start_date: startDate,
    end_date: endDate,
  });

  // Group activities by date
  const activitiesByDay = useMemo(() => {
    const map = new Map<string, Activity[]>();
    if (!data?.data) return map;
    for (const a of data.data) {
      if (!a.start_timestamp) continue;
      const day = a.start_timestamp.slice(0, 10);
      const existing = map.get(day) ?? [];
      existing.push(a);
      map.set(day, existing);
    }
    return map;
  }, [data]);

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfWeek(year, month);
  const today = new Date().toISOString().slice(0, 10);

  const monthLabel = currentDate.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  function prevMonth() {
    setCurrentDate(new Date(year, month - 1, 1));
    setSelectedDay(null);
  }

  function nextMonth() {
    setCurrentDate(new Date(year, month + 1, 1));
    setSelectedDay(null);
  }

  const selectedActivities = selectedDay ? activitiesByDay.get(selectedDay) ?? [] : [];

  if (isPending) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{monthLabel}</CardTitle>
          <div className="flex gap-1">
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={prevMonth}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={nextMonth}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Day headers */}
        <div className="grid grid-cols-7 gap-1 text-center">
          {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
            <div key={i} className="text-xs text-muted-foreground font-medium py-1">
              {d}
            </div>
          ))}
        </div>

        {/* Calendar grid */}
        <div className="grid grid-cols-7 gap-1">
          {/* Empty cells before first day */}
          {Array.from({ length: firstDay }).map((_, i) => (
            <div key={`empty-${i}`} className="aspect-square" />
          ))}

          {/* Day cells */}
          {Array.from({ length: daysInMonth }).map((_, i) => {
            const day = i + 1;
            const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const dayActivities = activitiesByDay.get(dateStr) ?? [];
            const isToday = dateStr === today;
            const isSelected = dateStr === selectedDay;

            return (
              <button
                key={day}
                onClick={() => setSelectedDay(isSelected ? null : dateStr)}
                className={`aspect-square rounded-md flex flex-col items-center justify-center gap-0.5 text-xs transition-colors
                  ${isToday ? "ring-1 ring-primary" : ""}
                  ${isSelected ? "bg-accent" : "hover:bg-accent/50"}
                `}
              >
                <span className={`${isToday ? "font-bold text-primary" : "text-muted-foreground"}`}>
                  {day}
                </span>
                {dayActivities.length > 0 && (
                  <div className="flex gap-0.5">
                    {dayActivities.slice(0, 3).map((a, j) => (
                      <div
                        key={j}
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: getColor(a.activity_type) }}
                      />
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 pt-2">
          {Object.entries(ACTIVITY_COLORS)
            .filter(([type]) => {
              // Only show types that appear in the current month
              for (const activities of activitiesByDay.values()) {
                if (activities.some((a) => a.activity_type === type)) return true;
              }
              return false;
            })
            .map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <div className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
                {activityTypeLabel(type)}
              </div>
            ))}
        </div>

        {/* Selected day activities */}
        {selectedDay && (
          <div className="border-t border-border pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">
              {new Date(selectedDay + "T12:00:00").toLocaleDateString("en-US", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </p>
            {selectedActivities.length === 0 ? (
              <p className="text-xs text-muted-foreground">Rest day</p>
            ) : (
              selectedActivities.map((a) => (
                <Link
                  key={a.activity_id}
                  href={`/activity/${a.activity_id}`}
                  className="flex items-center justify-between p-2 rounded-md hover:bg-accent/50 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: getColor(a.activity_type) }}
                    />
                    <span className="text-sm font-medium truncate">
                      {a.custom_name ?? a.activity_name ?? activityTypeLabel(a.activity_type)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                    {a.distance_meters ? <span>{formatDistance(a.distance_meters)}</span> : null}
                    {a.duration_seconds ? <span>{formatDuration(a.duration_seconds)}</span> : null}
                  </div>
                </Link>
              ))
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
