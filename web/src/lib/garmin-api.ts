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
} from "@/types/garmin";

export class GarminNotConnectedError extends Error {
  constructor() {
    super("Garmin account not connected");
    this.name = "GarminNotConnectedError";
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
    throw new Error(`Garmin API error: ${res.status}`);
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
    if (!res.ok) throw new Error(`Garmin API error: ${res.status}`);
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
      throw new Error(`Sync trigger error: ${res.status}`);
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
    if (!res.ok) throw new Error(`Garmin API error: ${res.status}`);
    return res.json() as Promise<PlannedWorkout>;
  },

  updatePlannedWorkout: async (id: number, body: PlannedWorkoutUpdate) => {
    const res = await fetch(`/api/garmin/planned-workouts/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...getHeaders() },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Garmin API error: ${res.status}`);
    return res.json() as Promise<PlannedWorkout>;
  },

  deletePlannedWorkout: async (id: number) => {
    const res = await fetch(`/api/garmin/planned-workouts/${id}`, {
      method: "DELETE",
      headers: getHeaders(),
    });
    if (!res.ok && res.status !== 204) throw new Error(`Garmin API error: ${res.status}`);
  },

  importPlannedWorkouts: async (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch("/api/garmin/planned-workouts/import", {
      method: "POST",
      headers: getHeaders(),
      body: formData,
    });
    if (!res.ok) throw new Error(`Garmin API error: ${res.status}`);
    return res.json() as Promise<BulkImportResult>;
  },
};
