import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { CoachingStatus, InviteCode } from "@/types/garmin";

async function coachingFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api/garmin/coaching/${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    let detail = `Error ${res.status}`;
    try {
      const json = JSON.parse(text);
      detail = json.detail || json.error || detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export function useCoachingStatus() {
  return useQuery<CoachingStatus>({
    queryKey: ["coaching-status"],
    queryFn: () => coachingFetch<CoachingStatus>("status"),
    retry: false,
    gcTime: 1000 * 60 * 10, // 10 min
  });
}

export function useGenerateInviteCode() {
  const queryClient = useQueryClient();
  return useMutation<InviteCode, Error>({
    mutationFn: () =>
      coachingFetch<InviteCode>("invite-codes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coaching-status"] });
      queryClient.invalidateQueries({ queryKey: ["invite-codes"] });
    },
    onError: (err) => toast.error(err.message),
  });
}

export function useInviteCodes() {
  return useQuery<InviteCode[]>({
    queryKey: ["invite-codes"],
    queryFn: () => coachingFetch<InviteCode[]>("invite-codes"),
    gcTime: 1000 * 60 * 10, // 10 min
  });
}

export function useRevokeInviteCode() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (code) =>
      coachingFetch<void>(`invite-codes/${code}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invite-codes"] });
      queryClient.invalidateQueries({ queryKey: ["coaching-status"] });
      toast.success("Invite code revoked");
    },
    onError: (err) => toast.error(err.message),
  });
}

export function useRedeemInviteCode() {
  const queryClient = useQueryClient();
  return useMutation<{ message: string }, Error, string>({
    mutationFn: (code) =>
      coachingFetch<{ message: string }>("redeem", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coaching-status"] });
      toast.success("Successfully linked to coach");
    },
    onError: (err) => toast.error(err.message),
  });
}

export function useRemoveAthlete() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (userId) =>
      coachingFetch<void>(`athletes/${userId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coaching-status"] });
      toast.success("Athlete removed");
    },
    onError: (err) => toast.error(err.message),
  });
}

export function useRemoveCoach() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (coachId) =>
      coachingFetch<void>(`coaches/${coachId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["coaching-status"] });
      toast.success("Coach removed");
    },
    onError: (err) => toast.error(err.message),
  });
}
