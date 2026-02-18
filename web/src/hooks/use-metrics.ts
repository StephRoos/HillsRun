import { useQuery } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";

export function useTrainingReadiness(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["training-readiness", queryParams],
    queryFn: () => garminApi.getTrainingReadiness(queryParams),
  });
}

export function useHrv(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["hrv", queryParams],
    queryFn: () => garminApi.getHrv(queryParams),
  });
}

export function useFitnessMetrics(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["fitness-metrics", queryParams],
    queryFn: () => garminApi.getFitnessMetrics(queryParams),
  });
}

export function useDailySummary(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["daily-summary", queryParams],
    queryFn: () => garminApi.getDailySummary(queryParams),
  });
}

export function useSleep(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["sleep", queryParams],
    queryFn: () => garminApi.getSleep(queryParams),
  });
}

export function useBodyBattery(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["body-battery", queryParams],
    queryFn: () => garminApi.getBodyBattery(queryParams),
  });
}

export function useBodyComposition(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["body-composition", queryParams],
    queryFn: () => garminApi.getBodyComposition(queryParams),
  });
}
