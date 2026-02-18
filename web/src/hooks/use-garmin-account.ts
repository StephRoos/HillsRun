import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

interface GarminAccountStatus {
  connected: boolean;
  garmin_display_name: string | null;
  user_id: number | null;
  last_sync: string | null;
}

interface ConnectResult {
  connected: boolean;
  needs_mfa?: boolean;
  mfa_session_id?: string;
  garmin_display_name?: string | null;
  user_id?: number | null;
}

async function parseErrorResponse(res: Response): Promise<string> {
  const text = await res.text();
  console.error("[garmin-auth] error response:", res.status, text);
  let data: Record<string, unknown> = {};
  try { data = JSON.parse(text); } catch { /* non-JSON */ }
  return (data.detail as string) || (data.error as string) || `Request failed (${res.status})`;
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
  return useMutation<ConnectResult, Error, { email: string; password: string }>({
    mutationFn: async (credentials) => {
      const res = await fetch("/api/garmin/auth/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials),
      });
      if (!res.ok) throw new Error(await parseErrorResponse(res));
      return res.json();
    },
    onSuccess: (data) => {
      if (data.needs_mfa) return; // MFA step — don't show success yet
      toast.success("Garmin account connected! Syncing your data...");
      queryClient.invalidateQueries({ queryKey: ["garmin-account"] });
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

export function useSubmitMfa() {
  const queryClient = useQueryClient();
  return useMutation<ConnectResult, Error, { mfa_session_id: string; mfa_code: string }>({
    mutationFn: async (payload) => {
      const res = await fetch("/api/garmin/auth/connect/mfa", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await parseErrorResponse(res));
      return res.json();
    },
    onSuccess: () => {
      toast.success("Garmin account connected! Syncing your data...");
      queryClient.invalidateQueries({ queryKey: ["garmin-account"] });
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
