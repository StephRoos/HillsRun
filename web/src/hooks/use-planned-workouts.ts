import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";
import { toast } from "sonner";
import type { PlannedWorkoutCreate, PlannedWorkoutUpdate } from "@/types/garmin";

export function usePlannedWorkouts(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);
  if (params?.offset) queryParams.offset = String(params.offset);

  return useQuery({
    queryKey: ["planned-workouts", queryParams],
    queryFn: () => garminApi.getPlannedWorkouts(queryParams),
  });
}

export function useCreatePlannedWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: PlannedWorkoutCreate) =>
      garminApi.createPlannedWorkout(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planned-workouts"] });
      toast.success("Workout planned");
    },
    onError: () => {
      toast.error("Failed to create planned workout");
    },
  });
}

export function useUpdatePlannedWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: PlannedWorkoutUpdate }) =>
      garminApi.updatePlannedWorkout(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planned-workouts"] });
      toast.success("Workout updated");
    },
    onError: () => {
      toast.error("Failed to update workout");
    },
  });
}

export function useDeletePlannedWorkout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => garminApi.deletePlannedWorkout(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["planned-workouts"] });
      toast.success("Workout deleted");
    },
    onError: () => {
      toast.error("Failed to delete workout");
    },
  });
}

export function useImportPlannedWorkouts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => garminApi.importPlannedWorkouts(file),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["planned-workouts"] });
      if (result.errors.length > 0) {
        toast.warning(`Imported ${result.imported} workouts with ${result.errors.length} errors`);
      } else {
        toast.success(`Imported ${result.imported} workouts`);
      }
    },
    onError: () => {
      toast.error("Failed to import workouts");
    },
  });
}
