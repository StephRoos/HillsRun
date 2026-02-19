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
} from "@/types/garmin";

export class GarminNotConnectedError extends Error {
  constructor() {
    super("Garmin account not connected");
    this.name = "GarminNotConnectedError";
  }
}

async function garminFetch<T>(
  path: string,
  params?: Record<string, string>
): Promise<T> {
  const url = new URL(`/api/garmin/${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }

  const res = await fetch(url.toString());
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Garmin API error: ${res.status}`);
    return res.json() as Promise<ActivityDetail>;
  },

  // Sync
  triggerSync: async (options?: { mode?: string; days_back?: number }) => {
    const res = await fetch("/api/garmin/sync/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
};
