import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface GarminAccountStatus {
  connected: boolean;
  garmin_display_name: string | null;
  user_id: number | null;
  last_sync: string | null;
}

export function useGarminAccount() {
  return useQuery<GarminAccountStatus>({
    queryKey: ["garmin-account"],
    queryFn: async () => {
      const res = await fetch("/api/garmin/auth/status");
      if (!res.ok) throw new Error("Failed to get Garmin account status");
      return res.json();
    },
  });
}

export function useConnectGarmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (credentials: { email: string; password: string }) => {
      const res = await fetch("/api/garmin/auth/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      if (!res.ok) {
        const text = await res.text();
        console.error("[connect-garmin] error response:", res.status, text);
        let data: Record<string, unknown> = {};
        try { data = JSON.parse(text); } catch { /* non-JSON response */ }
        const msg = (data.detail as string) || (data.error as string) || `Failed to connect Garmin account (${res.status})`;
        throw new Error(msg);
      }
      return res.json();
    },
    onSuccess: () => {
      toast.success("Garmin account connected! Syncing your data...");
      queryClient.invalidateQueries({ queryKey: ["garmin-account"] });
      // Trigger a sync
      fetch("/api/garmin/sync/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "full", days_back: 365 }),
      }).catch(() => {});
    },
    onError: (error: Error) => {
      toast.error(error.message);
    },
  });
}

export function useDisconnectGarmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await fetch("/api/garmin/auth/disconnect", {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to disconnect");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Garmin account disconnected");
      queryClient.invalidateQueries({ queryKey: ["garmin-account"] });
      queryClient.invalidateQueries({ queryKey: ["activities"] });
    },
    onError: () => {
      toast.error("Failed to disconnect Garmin account");
    },
  });
}
