import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { garminApi } from "@/lib/garmin-api";
import { toast } from "sonner";

export function useVma() {
  return useQuery({
    queryKey: ["vma"],
    queryFn: () => garminApi.getVma(),
  });
}

export function useUpdateVma() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vma: number | null) => garminApi.updateVma(vma),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vma"] });
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });
}
