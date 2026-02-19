"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useActivities } from "@/hooks/use-activities";
import { usePlannedWorkouts } from "@/hooks/use-planned-workouts";
import {
  formatDuration,
  formatDistance,
  activityTypeLabel,
  getActivityColor,
  ACTIVITY_COLORS,
} from "@/lib/utils";
import type { Activity, PlannedWorkout } from "@/types/garmin";

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

const MAX_CARDS = 2;

export function ActivityCalendar() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const startDate = new Date(year, month, 1).toISOString().slice(0, 10);
  const endDate = new Date(year, month + 1, 0).toISOString().slice(0, 10);

  const { data, isPending } = useActivities({
    limit: 100,
    start_date: startDate,
    end_date: endDate,
  });

  const { data: plannedData } = usePlannedWorkouts({
    start_date: startDate,
    end_date: endDate,
    limit: 200,
  });

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

  const plannedByDay = useMemo(() => {
    const map = new Map<string, PlannedWorkout[]>();
    if (!plannedData?.data) return map;
    for (const w of plannedData.data) {
      const existing = map.get(w.planned_date) ?? [];
      existing.push(w);
      map.set(w.planned_date, existing);
    }
    return map;
  }, [plannedData]);

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
  const selectedPlanned = selectedDay ? plannedByDay.get(selectedDay) ?? [] : [];

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
          {Array.from({ length: firstDay }).map((_, i) => (
            <div key={`empty-${i}`} className="min-h-[52px]" />
          ))}

          {Array.from({ length: daysInMonth }).map((_, i) => {
            const day = i + 1;
            const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const dayActivities = activitiesByDay.get(dateStr) ?? [];
            const dayPlanned = plannedByDay.get(dateStr) ?? [];
            const isToday = dateStr === today;
            const isSelected = dateStr === selectedDay;
            const totalItems = dayActivities.length + dayPlanned.length;
            const overflow = totalItems - MAX_CARDS;

            return (
              <button
                key={day}
                onClick={() => setSelectedDay(isSelected ? null : dateStr)}
                className={`min-h-[52px] rounded-md flex flex-col p-0.5 text-xs transition-colors
                  ${isToday ? "ring-1 ring-primary" : ""}
                  ${isSelected ? "bg-accent" : "hover:bg-accent/50"}
                `}
              >
                <span
                  className={`text-[10px] leading-4 px-0.5 ${isToday ? "font-bold text-primary" : "text-muted-foreground"}`}
                >
                  {day}
                </span>

                {/* Compact cards */}
                {dayActivities.slice(0, MAX_CARDS).map((a, j) => (
                  <div
                    key={`a-${j}`}
                    className="flex items-stretch rounded mt-0.5 overflow-hidden"
                    style={{ backgroundColor: `${getActivityColor(a.activity_type)}15` }}
                  >
                    <div
                      className="w-[2px] shrink-0"
                      style={{ backgroundColor: getActivityColor(a.activity_type) }}
                    />
                    <span className="text-[9px] leading-3 px-0.5 py-px truncate text-foreground">
                      {a.custom_name ?? a.activity_name ?? activityTypeLabel(a.activity_type)}
                    </span>
                  </div>
                ))}

                {dayPlanned
                  .slice(0, Math.max(0, MAX_CARDS - dayActivities.length))
                  .map((w, j) => (
                    <div
                      key={`p-${j}`}
                      className="flex items-stretch rounded mt-0.5 overflow-hidden"
                      style={{ backgroundColor: `${getActivityColor(w.sport_type)}10` }}
                    >
                      <div
                        className="w-[2px] shrink-0"
                        style={{
                          backgroundImage: `repeating-linear-gradient(to bottom, ${getActivityColor(w.sport_type)} 0px, ${getActivityColor(w.sport_type)} 2px, transparent 2px, transparent 4px)`,
                        }}
                      />
                      <span className="text-[9px] leading-3 px-0.5 py-px truncate text-foreground/60">
                        {w.title}
                      </span>
                    </div>
                  ))}

                {overflow > 0 && (
                  <span className="text-[8px] text-muted-foreground px-0.5">
                    +{overflow}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-3 pt-2">
          {Object.entries(ACTIVITY_COLORS)
            .filter(([type]) => {
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

        {/* Selected day details */}
        {selectedDay && (
          <div className="border-t border-border pt-3 space-y-2">
            <p className="text-xs font-medium text-muted-foreground">
              {new Date(selectedDay + "T12:00:00").toLocaleDateString("en-US", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </p>

            {selectedPlanned.map((w) => (
              <div
                key={`pw-${w.id}`}
                className="flex items-center justify-between p-2 rounded-md bg-accent/30"
              >
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ border: `1.5px dashed ${getActivityColor(w.sport_type)}` }}
                  />
                  <span className="text-sm font-medium truncate">{w.title}</span>
                  <span className="text-[10px] text-muted-foreground capitalize">{w.intensity}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                  {w.planned_distance_meters ? <span>{formatDistance(w.planned_distance_meters)}</span> : null}
                  {w.planned_duration_seconds ? <span>{formatDuration(w.planned_duration_seconds)}</span> : null}
                </div>
              </div>
            ))}

            {selectedActivities.map((a) => (
              <Link
                key={a.activity_id}
                href={`/activity/${a.activity_id}`}
                className="flex items-center justify-between p-2 rounded-md hover:bg-accent/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full shrink-0"
                    style={{ backgroundColor: getActivityColor(a.activity_type) }}
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
            ))}

            {selectedActivities.length === 0 && selectedPlanned.length === 0 && (
              <p className="text-xs text-muted-foreground">Rest day</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
