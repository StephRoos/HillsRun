"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreatePlannedWorkout,
  useUpdatePlannedWorkout,
  useDeletePlannedWorkout,
} from "@/hooks/use-planned-workouts";
import type { PlannedWorkout } from "@/types/garmin";

const SPORT_TYPES = [
  { value: "running", label: "Running" },
  { value: "trail_running", label: "Trail Running" },
  { value: "cycling", label: "Cycling" },
  { value: "swimming", label: "Swimming" },
  { value: "strength_training", label: "Strength Training" },
  { value: "rest", label: "Rest" },
  { value: "stretching", label: "Stretching" },
];

const INTENSITIES = ["easy", "moderate", "hard", "race"] as const;

interface WorkoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  date?: string;
  workout?: PlannedWorkout;
}

function WorkoutForm({
  workout,
  date,
  onClose,
}: {
  workout?: PlannedWorkout;
  date?: string;
  onClose: () => void;
}) {
  const isEdit = !!workout;

  const [plannedDate, setPlannedDate] = useState(
    workout?.planned_date ?? date ?? ""
  );
  const [sportType, setSportType] = useState(workout?.sport_type ?? "running");
  const [title, setTitle] = useState(workout?.title ?? "");
  const [description, setDescription] = useState(
    workout?.description ?? ""
  );
  const [durationMinutes, setDurationMinutes] = useState(
    workout?.planned_duration_seconds
      ? String(Math.round(workout.planned_duration_seconds / 60))
      : ""
  );
  const [distanceKm, setDistanceKm] = useState(
    workout?.planned_distance_meters
      ? String(workout.planned_distance_meters / 1000)
      : ""
  );
  const [intensity, setIntensity] = useState(workout?.intensity ?? "moderate");

  const createMutation = useCreatePlannedWorkout();
  const updateMutation = useUpdatePlannedWorkout();
  const deleteMutation = useDeletePlannedWorkout();

  function handleSave() {
    if (!title.trim() || !plannedDate) return;

    const data = {
      planned_date: plannedDate,
      sport_type: sportType,
      title: title.trim(),
      description: description.trim() || undefined,
      planned_duration_seconds: durationMinutes
        ? Math.round(parseFloat(durationMinutes) * 60)
        : undefined,
      planned_distance_meters: distanceKm
        ? parseFloat(distanceKm) * 1000
        : undefined,
      intensity,
    };

    if (isEdit) {
      updateMutation.mutate(
        { id: workout.id, body: data },
        { onSuccess: onClose }
      );
    } else {
      createMutation.mutate(data, { onSuccess: onClose });
    }
  }

  function handleDelete() {
    if (!workout) return;
    deleteMutation.mutate(workout.id, { onSuccess: onClose });
  }

  const isPending =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending;

  return (
    <>
      <DialogHeader>
        <DialogTitle>{isEdit ? "Edit Workout" : "Plan Workout"}</DialogTitle>
      </DialogHeader>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="date">Date</Label>
          <Input
            id="date"
            type="date"
            value={plannedDate}
            onChange={(e) => setPlannedDate(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="sport-type">Sport Type</Label>
          <Select value={sportType} onValueChange={setSportType}>
            <SelectTrigger id="sport-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SPORT_TYPES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Easy run"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Notes about this workout..."
            rows={2}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2">
            <Label htmlFor="duration">Duration (min)</Label>
            <Input
              id="duration"
              type="number"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
              placeholder="45"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="distance">Distance (km)</Label>
            <Input
              id="distance"
              type="number"
              step="0.1"
              value={distanceKm}
              onChange={(e) => setDistanceKm(e.target.value)}
              placeholder="10"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Intensity</Label>
          <div className="flex gap-1">
            {INTENSITIES.map((i) => (
              <Button
                key={i}
                type="button"
                size="sm"
                variant={intensity === i ? "default" : "outline"}
                className="flex-1 text-xs capitalize"
                onClick={() => setIntensity(i)}
              >
                {i}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <DialogFooter className="flex gap-2 sm:gap-0">
        {isEdit && (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleDelete}
            disabled={isPending}
            className="mr-auto"
          >
            Delete
          </Button>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          disabled={isPending}
        >
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={isPending || !title.trim() || !plannedDate}
        >
          {isPending ? "Saving..." : "Save"}
        </Button>
      </DialogFooter>
    </>
  );
}

export function WorkoutDialog({
  open,
  onOpenChange,
  date,
  workout,
}: WorkoutDialogProps) {
  // Use key to reset form state when dialog opens with different props
  const formKey = workout?.id ?? date ?? "new";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        {open && (
          <WorkoutForm
            key={formKey}
            workout={workout}
            date={date}
            onClose={() => onOpenChange(false)}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}
