"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
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
import { WorkoutDialog } from "./workout-dialog";
import type { Activity, PlannedWorkout } from "@/types/garmin";

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfWeek(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

function activityLabel(a: Activity): string {
  return a.custom_name ?? a.activity_name ?? activityTypeLabel(a.activity_type);
}

function activityMeta(a: Activity): string {
  const parts: string[] = [];
  if (a.distance_meters) parts.push(formatDistance(a.distance_meters));
  if (a.duration_seconds) parts.push(formatDuration(a.duration_seconds));
  return parts.join(" · ");
}

function plannedMeta(w: PlannedWorkout): string {
  const parts: string[] = [];
  if (w.planned_distance_meters) parts.push(formatDistance(w.planned_distance_meters));
  if (w.planned_duration_seconds) parts.push(formatDuration(w.planned_duration_seconds));
  return parts.join(" · ");
}

const MAX_CARDS = 3;

export function TrainingCalendar() {
  const [currentDate, setCurrentDate] = useState(() => new Date());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editWorkout, setEditWorkout] = useState<PlannedWorkout | undefined>();
  const [dialogDate, setDialogDate] = useState<string | undefined>();

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
  }

  function nextMonth() {
    setCurrentDate(new Date(year, month + 1, 1));
  }

  function goToToday() {
    setCurrentDate(new Date());
  }

  function openCreateDialog(date: string) {
    setEditWorkout(undefined);
    setDialogDate(date);
    setDialogOpen(true);
  }

  function openEditDialog(workout: PlannedWorkout) {
    setEditWorkout(workout);
    setDialogDate(workout.planned_date);
    setDialogOpen(true);
  }

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

      {/* Calendar grid */}
      <div>
        {/* Day headers */}
        <div className="grid grid-cols-7 gap-1 text-center mb-1">
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
            <div key={d} className="text-xs text-muted-foreground font-medium py-2">
              {d}
            </div>
          ))}
        </div>

        {/* Calendar cells */}
        <div className="grid grid-cols-7 gap-1">
          {Array.from({ length: firstDay }).map((_, i) => (
            <div key={`empty-${i}`} className="min-h-[100px]" />
          ))}

          {Array.from({ length: daysInMonth }).map((_, i) => {
            const day = i + 1;
            const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const dayActivities = activitiesByDay.get(dateStr) ?? [];
            const dayPlanned = plannedByDay.get(dateStr) ?? [];
            const isToday = dateStr === today;
            const totalItems = dayActivities.length + dayPlanned.length;
            const overflow = totalItems - MAX_CARDS;

            return (
              <div
                key={day}
                className={`min-h-[100px] rounded-lg border p-1 flex flex-col gap-0.5 transition-colors group
                  ${isToday ? "ring-2 ring-primary border-primary/30" : "border-border hover:border-border/80 hover:bg-accent/30"}
                `}
              >
                {/* Day number + add button */}
                <div className="flex items-center justify-between px-0.5">
                  <span
                    className={`text-xs leading-5 ${isToday ? "font-bold text-primary" : "text-muted-foreground"}`}
                  >
                    {day}
                  </span>
                  <button
                    onClick={() => openCreateDialog(dateStr)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity h-4 w-4 flex items-center justify-center rounded hover:bg-accent"
                  >
                    <Plus className="h-3 w-3 text-muted-foreground" />
                  </button>
                </div>

                {/* Activity cards (completed first, then planned) */}
                {dayActivities.slice(0, MAX_CARDS).map((a) => (
                  <Link
                    key={`a-${a.activity_id}`}
                    href={`/activity/${a.activity_id}`}
                    className="flex items-stretch rounded text-[10px] leading-tight hover:brightness-125 transition-all overflow-hidden"
                    style={{ backgroundColor: `${getActivityColor(a.activity_type)}15` }}
                  >
                    <div
                      className="w-[3px] shrink-0 rounded-l"
                      style={{ backgroundColor: getActivityColor(a.activity_type) }}
                    />
                    <div className="px-1 py-0.5 min-w-0">
                      <div className="font-medium truncate text-foreground">
                        {activityLabel(a)}
                      </div>
                      {activityMeta(a) && (
                        <div className="text-muted-foreground truncate">
                          {activityMeta(a)}
                        </div>
                      )}
                    </div>
                  </Link>
                ))}

                {dayPlanned
                  .slice(0, Math.max(0, MAX_CARDS - dayActivities.length))
                  .map((w) => (
                    <button
                      key={`p-${w.id}`}
                      onClick={() => openEditDialog(w)}
                      className="flex items-stretch rounded text-[10px] leading-tight hover:brightness-125 transition-all overflow-hidden text-left"
                      style={{ backgroundColor: `${getActivityColor(w.sport_type)}10` }}
                    >
                      <div
                        className="w-[3px] shrink-0 rounded-l"
                        style={{
                          backgroundImage: `repeating-linear-gradient(to bottom, ${getActivityColor(w.sport_type)} 0px, ${getActivityColor(w.sport_type)} 3px, transparent 3px, transparent 6px)`,
                        }}
                      />
                      <div className="px-1 py-0.5 min-w-0">
                        <div className="font-medium truncate text-foreground/70">
                          {w.title}
                        </div>
                        {plannedMeta(w) && (
                          <div className="text-muted-foreground truncate">
                            {plannedMeta(w)}
                          </div>
                        )}
                      </div>
                    </button>
                  ))}

                {overflow > 0 && (
                  <span className="text-[10px] text-muted-foreground px-1">
                    +{overflow} more
                  </span>
                )}
              </div>
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
                  style={{ backgroundColor: getActivityColor(type) }}
                />
                {activityTypeLabel(type)}
              </div>
            ))}
          {activeSportTypes.size > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div
                className="h-2 w-2 rounded-full"
                style={{ border: "1.5px dashed #94A3B8" }}
              />
              Planned
            </div>
          )}
        </div>
      </div>

      <WorkoutDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        date={dialogDate}
        workout={editWorkout}
      />
    </>
  );
}
