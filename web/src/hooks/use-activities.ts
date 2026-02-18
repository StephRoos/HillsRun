import { useQuery } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";

export function useActivities(params?: {
  limit?: number;
  offset?: number;
  activity_type?: string;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.limit) queryParams.limit = String(params.limit);
  if (params?.offset) queryParams.offset = String(params.offset);
  if (params?.activity_type) queryParams.activity_type = params.activity_type;

  return useQuery({
    queryKey: ["activities", queryParams],
    queryFn: () => garminApi.getActivities(queryParams),
  });
}

export function useActivity(id: string) {
  return useQuery({
    queryKey: ["activity", id],
    queryFn: () => garminApi.getActivity(id),
    enabled: !!id,
  });
}

export function useActivitySplits(id: string) {
  return useQuery({
    queryKey: ["activity-splits", id],
    queryFn: () => garminApi.getActivitySplits(id),
    enabled: !!id,
  });
}
