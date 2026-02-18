import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";

export function useActivities(params?: {
  limit?: number;
  offset?: number;
  activity_type?: string;
  start_date?: string;
  end_date?: string;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.limit) queryParams.limit = String(params.limit);
  if (params?.offset) queryParams.offset = String(params.offset);
  if (params?.activity_type) queryParams.activity_type = params.activity_type;
  if (params?.start_date) queryParams.start_date = params.start_date;
  if (params?.end_date) queryParams.end_date = params.end_date;

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

export function useUpdateActivity(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { custom_name: string | null }) =>
      garminApi.updateActivity(id, body),
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: ["activity", id] });
      const previous = queryClient.getQueryData(["activity", id]);
      queryClient.setQueryData(["activity", id], (old: Record<string, unknown> | undefined) =>
        old ? { ...old, custom_name: body.custom_name } : old
      );
      return { previous };
    },
    onError: (_err, _body, context) => {
      if (context?.previous) {
        queryClient.setQueryData(["activity", id], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["activity", id] });
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
  });
}
