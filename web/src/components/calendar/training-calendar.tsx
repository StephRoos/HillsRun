"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useActivities } from "@/hooks/use-activities";
import { usePlannedWorkouts } from "@/hooks/use-planned-workouts";
import { formatDuration, formatDistance, activityTypeLabel } from "@/lib/utils";
import { WorkoutDialog } from "./workout-dialog";
import type { Activity, PlannedWorkout } from "@/types/garmin";

const ACTIVITY_COLORS: Record<string, string> = {
  running: "#FF8C00",
  trail_running: "#FF6B00",
  hiking: "#10B981",
  cycling: "#0891B2",
  swimming: "#0EA5E9",
  strength_training: "#8B5CF6",
  yoga: "#EC4899",
  walking: "#6B7280",
  rest: "#94A3B8",
  stretching: "#F472B6",
};

function getColor(type: string | null): string {
  return ACTIVITY_COLORS[type ?? ""] ?? "#94A3B8";
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

const INTENSITY_COLORS: Record<string, string> = {
  easy: "bg-green-500/10 text-green-500",
  moderate: "bg-yellow-500/10 text-yellow-500",
  hard: "bg-orange-500/10 text-orange-500",
  race: "bg-red-500/10 text-red-500",
};

export function TrainingCalendar() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editWorkout, setEditWorkout] = useState<PlannedWorkout | undefined>();

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const startDate = new Date(year, month, 1).toISOString().slice(0, 10);
  const endDate = new Date(year, month + 1, 0).toISOString().slice(0, 10);

  const { data: activitiesData, isPending: activitiesLoading } = useActivities({
    limit: 200,
    start_date: startDate,
    end_date: endDate,
  });

  const { data: plannedData, isPending: plannedLoading } = usePlannedWorkouts({
    start_date: startDate,
    end_date: endDate,
    limit: 200,
  });

  const isPending = activitiesLoading || plannedLoading;

  const activitiesByDay = useMemo(() => {
    const map = new Map<string, Activity[]>();
    if (!activitiesData?.data) return map;
    for (const a of activitiesData.data) {
      if (!a.start_timestamp) continue;
      const day = a.start_timestamp.slice(0, 10);
      const existing = map.get(day) ?? [];
      existing.push(a);
      map.set(day, existing);
    }
    return map;
  }, [activitiesData]);

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

  function goToToday() {
    setCurrentDate(new Date());
    setSelectedDay(new Date().toISOString().slice(0, 10));
  }

  function openCreateDialog(date?: string) {
    setEditWorkout(undefined);
    setDialogOpen(true);
    if (date) setSelectedDay(date);
  }

  function openEditDialog(workout: PlannedWorkout) {
    setEditWorkout(workout);
    setDialogOpen(true);
  }

  const selectedActivities = selectedDay
    ? activitiesByDay.get(selectedDay) ?? []
    : [];
  const selectedPlanned = selectedDay
    ? plannedByDay.get(selectedDay) ?? []
    : [];

  // Collect active sport types for legend
  const activeSportTypes = useMemo(() => {
    const types = new Set<string>();
    for (const activities of activitiesByDay.values()) {
      for (const a of activities) {
        if (a.activity_type) types.add(a.activity_type);
      }
    }
    for (const workouts of plannedByDay.values()) {
      for (const w of workouts) {
        types.add(w.sport_type);
      }
    }
    return types;
  }, [activitiesByDay, plannedByDay]);

  if (isPending) {
    return <Skeleton className="h-[500px] w-full" />;
  }

  return (
    <>
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={prevMonth}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <h2 className="text-lg font-semibold min-w-[160px] text-center">
            {monthLabel}
          </h2>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={nextMonth}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="text-xs" onClick={goToToday}>
            Today
          </Button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Calendar grid */}
        <div className="flex-1">
          {/* Day headers */}
          <div className="grid grid-cols-7 gap-1 text-center mb-1">
            {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
              <div key={d} className="text-xs text-muted-foreground font-medium py-2">
                {d}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-1">
            {Array.from({ length: firstDay }).map((_, i) => (
              <div key={`empty-${i}`} className="aspect-square" />
            ))}

            {Array.from({ length: daysInMonth }).map((_, i) => {
              const day = i + 1;
              const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const dayActivities = activitiesByDay.get(dateStr) ?? [];
              const dayPlanned = plannedByDay.get(dateStr) ?? [];
              const isToday = dateStr === today;
              const isSelected = dateStr === selectedDay;

              return (
                <button
                  key={day}
                  onClick={() => setSelectedDay(isSelected ? null : dateStr)}
                  className={`aspect-square rounded-lg flex flex-col items-center justify-center gap-0.5 text-sm transition-colors border
                    ${isToday ? "ring-2 ring-primary" : ""}
                    ${isSelected ? "bg-accent border-accent-foreground/20" : "border-transparent hover:bg-accent/50"}
                  `}
                >
                  <span
                    className={`${isToday ? "font-bold text-primary" : "text-muted-foreground"}`}
                  >
                    {day}
                  </span>
                  <div className="flex gap-0.5 flex-wrap justify-center">
                    {/* Completed activity dots (filled) */}
                    {dayActivities.slice(0, 3).map((a, j) => (
                      <div
                        key={`a-${j}`}
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ backgroundColor: getColor(a.activity_type) }}
                      />
                    ))}
                    {/* Planned workout dots (dashed outline) */}
                    {dayPlanned.slice(0, 3).map((w, j) => (
                      <div
                        key={`p-${j}`}
                        className="h-1.5 w-1.5 rounded-full"
                        style={{
                          border: `1px dashed ${getColor(w.sport_type)}`,
                        }}
                      />
                    ))}
                  </div>
                </button>
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mt-4">
            {Array.from(activeSportTypes)
              .filter((type) => type in ACTIVITY_COLORS)
              .map((type) => (
                <div
                  key={type}
                  className="flex items-center gap-1.5 text-xs text-muted-foreground"
                >
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: getColor(type) }}
                  />
                  {activityTypeLabel(type)}
                </div>
              ))}
            {activeSportTypes.size > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <div
                  className="h-2 w-2 rounded-full"
                  style={{ border: "1px dashed #94A3B8" }}
                />
                Planned
              </div>
            )}
          </div>
        </div>

        {/* Side panel */}
        {selectedDay && (
          <div className="lg:w-80 border rounded-lg p-4 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">
                {new Date(selectedDay + "T12:00:00").toLocaleDateString(
                  "en-US",
                  { weekday: "long", day: "numeric", month: "long" }
                )}
              </p>
              <Button
                size="sm"
                variant="outline"
                className="gap-1"
                onClick={() => openCreateDialog(selectedDay)}
              >
                <Plus className="h-3 w-3" />
                Add
              </Button>
            </div>

            {/* Planned workouts */}
            {selectedPlanned.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Planned
                </p>
                {selectedPlanned.map((w) => (
                  <button
                    key={w.id}
                    onClick={() => openEditDialog(w)}
                    className="w-full text-left p-2 rounded-md hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div
                          className="h-2 w-2 rounded-full shrink-0"
                          style={{
                            border: `1.5px dashed ${getColor(w.sport_type)}`,
                          }}
                        />
                        <span className="text-sm font-medium">{w.title}</span>
                      </div>
                      <Badge
                        variant="secondary"
                        className={`text-[10px] ${INTENSITY_COLORS[w.intensity] ?? ""}`}
                      >
                        {w.intensity}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground pl-4">
                      {w.planned_distance_meters && (
                        <span>{formatDistance(w.planned_distance_meters)}</span>
                      )}
                      {w.planned_duration_seconds && (
                        <span>{formatDuration(w.planned_duration_seconds)}</span>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}

            {/* Completed activities */}
            {selectedActivities.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Completed
                </p>
                {selectedActivities.map((a) => (
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
                        {a.custom_name ??
                          a.activity_name ??
                          activityTypeLabel(a.activity_type)}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                      {a.distance_meters ? (
                        <span>{formatDistance(a.distance_meters)}</span>
                      ) : null}
                      {a.duration_seconds ? (
                        <span>{formatDuration(a.duration_seconds)}</span>
                      ) : null}
                    </div>
                  </Link>
                ))}
              </div>
            )}

            {selectedPlanned.length === 0 && selectedActivities.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No activities or planned workouts
              </p>
            )}
          </div>
        )}
      </div>

      <WorkoutDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        date={selectedDay ?? undefined}
        workout={editWorkout}
      />
    </>
  );
}
