import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useTrainingPlans,
  useTrainingPlan,
  useTrainingPlanWeek,
  useGenerateTrainingPlan,
  useUpdateTrainingPlanStatus,
  useDeleteTrainingPlan,
  useAthleteProfile,
  useUpdateAthleteProfile,
  useRaceTargets,
  useCreateRaceTarget,
  useDeleteRaceTarget,
  useFitnessSnapshot,
} from "../use-training-plans";
import * as garminApiModule from "@/lib/garmin-api";

vi.mock("@/lib/garmin-api");
const { mockToast } = vi.hoisted(() => ({
  mockToast: { error: vi.fn(), success: vi.fn() },
}));
vi.mock("sonner", () => ({ toast: mockToast }));

const mockGarminApi = vi.mocked(garminApiModule.garminApi);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }
  return Wrapper;
}

describe("useTrainingPlans", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches all training plans", async () => {
    const plans = [{ id: 1, name: "Marathon prep", status: "active" }];
    mockGarminApi.getTrainingPlans.mockResolvedValueOnce(plans);

    const { result } = renderHook(() => useTrainingPlans(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(plans);
  });
});

describe("useTrainingPlan", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches a single plan by id", async () => {
    const plan = { id: 1, name: "Marathon prep", weeks: 12 };
    mockGarminApi.getTrainingPlan.mockResolvedValueOnce(plan);

    const { result } = renderHook(() => useTrainingPlan(1), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(plan);
    expect(mockGarminApi.getTrainingPlan).toHaveBeenCalledWith(1);
  });

  it("is disabled when planId is null", () => {
    const { result } = renderHook(() => useTrainingPlan(null), {
      wrapper: createWrapper(),
    });

    expect(mockGarminApi.getTrainingPlan).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useTrainingPlanWeek", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches a specific week", async () => {
    const weekData = { week_number: 3, workouts: [] };
    mockGarminApi.getTrainingPlanWeek.mockResolvedValueOnce(weekData);

    const { result } = renderHook(() => useTrainingPlanWeek(1, 3), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGarminApi.getTrainingPlanWeek).toHaveBeenCalledWith(1, 3);
  });
});

describe("useGenerateTrainingPlan", () => {
  beforeEach(() => vi.clearAllMocks());

  it("generates plan and shows toast", async () => {
    mockGarminApi.generateTrainingPlan.mockResolvedValueOnce({ id: 2 });

    const { result } = renderHook(() => useGenerateTrainingPlan(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        race_name: "Trail 50K",
        race_date: "2025-09-01",
      } as any);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockToast.success).toHaveBeenCalledWith("Training plan generated");
  });

  it("shows error message from API", async () => {
    mockGarminApi.generateTrainingPlan.mockRejectedValueOnce(
      new Error("Insufficient data for plan generation")
    );

    const { result } = renderHook(() => useGenerateTrainingPlan(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ race_name: "Test" } as any);
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockToast.error).toHaveBeenCalledWith(
      "Insufficient data for plan generation"
    );
  });
});

describe("useUpdateTrainingPlanStatus", () => {
  beforeEach(() => vi.clearAllMocks());

  it("updates status and shows toast", async () => {
    mockGarminApi.updateTrainingPlanStatus.mockResolvedValueOnce({ status: "completed" });

    const { result } = renderHook(() => useUpdateTrainingPlanStatus(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ planId: 1, status: "completed" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGarminApi.updateTrainingPlanStatus).toHaveBeenCalledWith(1, "completed");
    expect(mockToast.success).toHaveBeenCalledWith("Plan status updated");
  });
});

describe("useDeleteTrainingPlan", () => {
  beforeEach(() => vi.clearAllMocks());

  it("deletes plan and shows toast", async () => {
    mockGarminApi.deleteTrainingPlan.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteTrainingPlan(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(1);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGarminApi.deleteTrainingPlan).toHaveBeenCalledWith(1);
    expect(mockToast.success).toHaveBeenCalledWith("Training plan deleted");
  });

  it("shows error toast on failure", async () => {
    mockGarminApi.deleteTrainingPlan.mockRejectedValueOnce(new Error("fail"));

    const { result } = renderHook(() => useDeleteTrainingPlan(), {
      wrapper: createWrapper(),
    });

    act(() => result.current.mutate(1));

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(mockToast.error).toHaveBeenCalledWith("Failed to delete training plan");
  });
});

describe("useAthleteProfile", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches athlete profile", async () => {
    const profile = { vma: 18.5, weight: 72 };
    mockGarminApi.getAthleteProfile.mockResolvedValueOnce(profile);

    const { result } = renderHook(() => useAthleteProfile(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(profile);
  });

  it("does not retry on error", async () => {
    mockGarminApi.getAthleteProfile.mockRejectedValueOnce(new Error("404"));

    const { result } = renderHook(() => useAthleteProfile(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    // retry: false — should only call once
    expect(mockGarminApi.getAthleteProfile).toHaveBeenCalledTimes(1);
  });
});

describe("useUpdateAthleteProfile", () => {
  beforeEach(() => vi.clearAllMocks());

  it("updates profile and shows toast", async () => {
    mockGarminApi.updateAthleteProfile.mockResolvedValueOnce({ vma: 19 });

    const { result } = renderHook(() => useUpdateAthleteProfile(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ vma: 19 } as any);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockToast.success).toHaveBeenCalledWith("Profile updated");
  });
});

describe("useRaceTargets", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches race targets", async () => {
    const targets = [{ id: 1, race_name: "UTMB", target_time: "30:00:00" }];
    mockGarminApi.getRaceTargets.mockResolvedValueOnce(targets);

    const { result } = renderHook(() => useRaceTargets(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(targets);
  });
});

describe("useCreateRaceTarget", () => {
  beforeEach(() => vi.clearAllMocks());

  it("creates target and shows toast", async () => {
    mockGarminApi.createRaceTarget.mockResolvedValueOnce({ id: 2 });

    const { result } = renderHook(() => useCreateRaceTarget(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ race_name: "OCC", distance_km: 56 } as any);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockToast.success).toHaveBeenCalledWith("Race target created");
  });
});

describe("useDeleteRaceTarget", () => {
  beforeEach(() => vi.clearAllMocks());

  it("deletes target and shows toast", async () => {
    mockGarminApi.deleteRaceTarget.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeleteRaceTarget(), {
      wrapper: createWrapper(),
    });

    act(() => result.current.mutate(5));

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockGarminApi.deleteRaceTarget).toHaveBeenCalledWith(5);
    expect(mockToast.success).toHaveBeenCalledWith("Race target deleted");
  });
});

describe("useFitnessSnapshot", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches fitness snapshot", async () => {
    const snapshot = { vo2max: 55, training_load: 120 };
    mockGarminApi.getFitnessSnapshot.mockResolvedValueOnce(snapshot);

    const { result } = renderHook(() => useFitnessSnapshot(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(snapshot);
  });
});
