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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
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
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
  });
}

export function useStress(params?: {
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;
  if (params?.limit) queryParams.limit = String(params.limit);

  return useQuery({
    queryKey: ["stress", queryParams],
    queryFn: () => garminApi.getStress(queryParams),
    gcTime: 1000 * 60 * 60, // 1 hour — historical metric data
  });
}
