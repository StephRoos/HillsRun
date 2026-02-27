import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";
import { toast } from "sonner";
import type {
  AthleteProfileCreate,
  GeneratePlanRequest,
} from "@/types/garmin";

export function useTrainingPlans() {
  return useQuery({
    queryKey: ["training-plans"],
    queryFn: () => garminApi.getTrainingPlans(),
  });
}

export function useTrainingPlan(planId: number | null) {
  return useQuery({
    queryKey: ["training-plans", planId],
    queryFn: () => garminApi.getTrainingPlan(planId!),
    enabled: planId !== null,
  });
}

export function useTrainingPlanWeek(planId: number, weekNumber: number) {
  return useQuery({
    queryKey: ["training-plans", planId, "weeks", weekNumber],
    queryFn: () => garminApi.getTrainingPlanWeek(planId, weekNumber),
  });
}

export function useGenerateTrainingPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: GeneratePlanRequest) =>
      garminApi.generateTrainingPlan(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["training-plans"] });
      queryClient.invalidateQueries({ queryKey: ["planned-workouts"] });
      toast.success("Training plan generated");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to generate training plan");
    },
  });
}

export function useUpdateTrainingPlanStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ planId, status }: { planId: number; status: string }) =>
      garminApi.updateTrainingPlanStatus(planId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["training-plans"] });
      toast.success("Plan status updated");
    },
    onError: () => {
      toast.error("Failed to update plan status");
    },
  });
}

export function useDeleteTrainingPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (planId: number) => garminApi.deleteTrainingPlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["training-plans"] });
      queryClient.invalidateQueries({ queryKey: ["planned-workouts"] });
      toast.success("Training plan deleted");
    },
    onError: () => {
      toast.error("Failed to delete training plan");
    },
  });
}

export function useAthleteProfile() {
  return useQuery({
    queryKey: ["athlete-profile"],
    queryFn: () => garminApi.getAthleteProfile(),
    retry: false,
  });
}

export function useUpdateAthleteProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AthleteProfileCreate) =>
      garminApi.updateAthleteProfile(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["athlete-profile"] });
      toast.success("Profile updated");
    },
    onError: () => {
      toast.error("Failed to update profile");
    },
  });
}

export function useRaceTargets() {
  return useQuery({
    queryKey: ["race-targets"],
    queryFn: () => garminApi.getRaceTargets(),
  });
}

export function useCreateRaceTarget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: import("@/types/garmin").RaceTargetCreate) =>
      garminApi.createRaceTarget(body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["race-targets"] });
      toast.success("Race target created");
    },
    onError: () => {
      toast.error("Failed to create race target");
    },
  });
}

export function useDeleteRaceTarget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (raceId: number) => garminApi.deleteRaceTarget(raceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["race-targets"] });
      toast.success("Race target deleted");
    },
    onError: () => {
      toast.error("Failed to delete race target");
    },
  });
}

export function useFitnessSnapshot() {
  return useQuery({
    queryKey: ["fitness-snapshot"],
    queryFn: () => garminApi.getFitnessSnapshot(),
    staleTime: 15 * 60 * 1000, // 15 minutes
  });
}
