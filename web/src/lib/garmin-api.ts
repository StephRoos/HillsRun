import type {
  Page,
  Activity,
  ActivityDetail,
  ActivitySplit,
  DailySummary,
  SleepData,
  BodyBattery,
  StressData,
  HrvData,
  TrainingReadiness,
  FitnessMetrics,
  BodyComposition,
  PlannedWorkout,
  PlannedWorkoutCreate,
  PlannedWorkoutUpdate,
  BulkImportResult,
  VmaData,
  AthleteProfile,
  AthleteProfileCreate,
  RaceTarget,
  RaceTargetCreate,
  GeneratePlanRequest,
  TrainingPlanSummary,
  TrainingPlanDetail,
  PlanWeekDetail,
  FitnessSnapshot,
} from "@/types/garmin";

export class GarminNotConnectedError extends Error {
  constructor() {
    super("Garmin account not connected");
    this.name = "GarminNotConnectedError";
  }
}

async function parseErrorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.error ?? body.detail ?? `Garmin API error: ${res.status}`;
  } catch {
    return `Garmin API error: ${res.status}`;
  }
}

let _viewAsAthleteId: number | null = null;

export function setViewAsAthlete(id: number | null) {
  _viewAsAthleteId = id;
}

function getHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
  if (_viewAsAthleteId !== null) {
    h["X-View-As-Athlete"] = String(_viewAsAthleteId);
  }
  return h;
}

async function garminFetch<T>(
  path: string,
  params?: Record<string, string>
): Promise<T> {
  const url = new URL(`/api/garmin/${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }

  const res = await fetch(url.toString(), { headers: getHeaders() });
  if (!res.ok) {
    if (res.status === 403) {
      throw new GarminNotConnectedError();
    }
    const message = await parseErrorMessage(res);
    throw new Error(message);
  }
  return res.json();
}

export const garminApi = {
  // Activities
  getActivities: (params?: Record<string, string>) =>
    garminFetch<Page<Activity>>("activities", params),

  getActivity: (id: string) =>
    garminFetch<ActivityDetail>(`activities/${id}`),

  getActivitySplits: (id: string) =>
    garminFetch<Page<ActivitySplit>>(`activities/${id}/splits`),

  // Daily health
  getDailySummary: (params?: Record<string, string>) =>
    garminFetch<Page<DailySummary>>("daily/summary", params),

  getSleep: (params?: Record<string, string>) =>
    garminFetch<Page<SleepData>>("daily/sleep", params),

  getBodyBattery: (params?: Record<string, string>) =>
    garminFetch<Page<BodyBattery>>("daily/body-battery", params),

  getStress: (params?: Record<string, string>) =>
    garminFetch<Page<StressData>>("daily/stress", params),

  // Advanced metrics
  getHrv: (params?: Record<string, string>) =>
    garminFetch<Page<HrvData>>("metrics/hrv", params),

  getTrainingReadiness: (params?: Record<string, string>) =>
    garminFetch<Page<TrainingReadiness>>("metrics/training-readiness", params),

  getFitnessMetrics: (params?: Record<string, string>) =>
    garminFetch<Page<FitnessMetrics>>("metrics/fitness", params),

  // Body
  getBodyComposition: (params?: Record<string, string>) =>
    garminFetch<Page<BodyComposition>>("body/composition", params),

  updateActivity: async (id: string, body: { custom_name: string | null }) => {
    const res = await fetch(`/api/garmin/activities/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<ActivityDetail>;
  },

  // Sync
  triggerSync: async (options?: { mode?: string; days_back?: number }) => {
    const res = await fetch("/api/garmin/sync/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(options ?? {}),
    });
    if (!res.ok && res.status !== 409) {
      throw new Error(await parseErrorMessage(res));
    }
    return res.json();
  },

  getSyncStatus: () => garminFetch<Record<string, unknown>>("sync/status"),

  getSyncJob: (jobId: string) =>
    garminFetch<{ status: string; error: string | null }>(
      `sync/jobs/${jobId}`
    ),

  // Planned workouts
  getPlannedWorkouts: (params?: Record<string, string>) =>
    garminFetch<Page<PlannedWorkout>>("planned-workouts", params),

  getPlannedWorkout: (id: number) =>
    garminFetch<PlannedWorkout>(`planned-workouts/${id}`),

  createPlannedWorkout: async (body: PlannedWorkoutCreate) => {
    const res = await fetch("/api/garmin/planned-workouts", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<PlannedWorkout>;
  },

  updatePlannedWorkout: async (id: number, body: PlannedWorkoutUpdate) => {
    const res = await fetch(`/api/garmin/planned-workouts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<PlannedWorkout>;
  },

  deletePlannedWorkout: async (id: number) => {
    const res = await fetch(`/api/garmin/planned-workouts/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok && res.status !== 204) throw new Error(await parseErrorMessage(res));
  },

  // User profile
  getVma: () => garminFetch<VmaData>("user/vma"),

  updateVma: async (vma: number | null) => {
    const res = await fetch("/api/garmin/user/vma", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ vma }),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<VmaData>;
  },

  importPlannedWorkouts: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/garmin/planned-workouts/import", {
      method: "POST",
      headers: getHeaders(),
      body: formData,
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<BulkImportResult>;
  },

  // Training Plans
  getTrainingPlans: (params?: Record<string, string>) =>
    garminFetch<Page<TrainingPlanSummary>>("training-plans", params),

  getTrainingPlan: (planId: number) =>
    garminFetch<TrainingPlanDetail>(`training-plans/${planId}`),

  getTrainingPlanWeek: (planId: number, weekNumber: number) =>
    garminFetch<PlanWeekDetail>(`training-plans/${planId}/weeks/${weekNumber}`),

  generateTrainingPlan: async (body: GeneratePlanRequest) => {
    const res = await fetch("/api/garmin/training-plans/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<Record<string, unknown>>;
  },

  updateTrainingPlanStatus: async (planId: number, status: string) => {
    const res = await fetch(`/api/garmin/training-plans/${planId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify({ status }),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<TrainingPlanSummary>;
  },

  deleteTrainingPlan: async (planId: number) => {
    const res = await fetch(`/api/garmin/training-plans/${planId}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok && res.status !== 204) throw new Error(await parseErrorMessage(res));
  },

  // Athlete Profile
  getAthleteProfile: () =>
    garminFetch<AthleteProfile>("training-plans/profile"),

  updateAthleteProfile: async (body: AthleteProfileCreate) => {
    const res = await fetch("/api/garmin/training-plans/profile", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<AthleteProfile>;
  },

  // Race Targets
  getRaceTargets: () =>
    garminFetch<RaceTarget[]>("training-plans/races"),

  createRaceTarget: async (body: RaceTargetCreate) => {
    const res = await fetch("/api/garmin/training-plans/races", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await parseErrorMessage(res));
    return res.json() as Promise<RaceTarget>;
  },

  deleteRaceTarget: async (raceId: number) => {
    const res = await fetch(`/api/garmin/training-plans/races/${raceId}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok && res.status !== 204) throw new Error(await parseErrorMessage(res));
  },

  // Fitness Snapshot
  getFitnessSnapshot: () =>
    garminFetch<FitnessSnapshot>("training-plans/fitness-snapshot"),
};
