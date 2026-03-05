import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  usePlannedWorkouts,
  useCreatePlannedWorkout,
  useUpdatePlannedWorkout,
  useDeletePlannedWorkout,
  useImportPlannedWorkouts,
} from "../use-planned-workouts";
import * as garminApiModule from "@/lib/garmin-api";

vi.mock("@/lib/garmin-api");
const { mockToast } = vi.hoisted(() => ({
  mockToast: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
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

describe("usePlannedWorkouts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches planned workouts with default params", async () => {
    const mockData = {
      data: [{ id: 1, title: "Easy run", scheduled_date: "2024-06-01" }],
      pagination: { total: 1, limit: 50, offset: 0, has_more: false },
    };
    mockGarminApi.getPlannedWorkouts.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => usePlannedWorkouts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockData);
    expect(mockGarminApi.getPlannedWorkouts).toHaveBeenCalledWith({});
  });

  it("passes date range params", async () => {
    mockGarminApi.getPlannedWorkouts.mockResolvedValueOnce({ data: [], pagination: { total: 0, limit: 50, offset: 0, has_more: false } });

    const { result } = renderHook(
      () => usePlannedWorkouts({ start_date: "2024-06-01", end_date: "2024-06-30" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.getPlannedWorkouts).toHaveBeenCalledWith({
      start_date: "2024-06-01",
      end_date: "2024-06-30",
    });
  });

  it("passes pagination params as strings", async () => {
    mockGarminApi.getPlannedWorkouts.mockResolvedValueOnce({ data: [], pagination: { total: 0, limit: 10, offset: 20, has_more: false } });

    const { result } = renderHook(
      () => usePlannedWorkouts({ limit: 10, offset: 20 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.getPlannedWorkouts).toHaveBeenCalledWith({
      limit: "10",
      offset: "20",
    });
  });
});

describe("useCreatePlannedWorkout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates workout and shows success toast", async () => {
    mockGarminApi.createPlannedWorkout.mockResolvedValueOnce({ id: 1 });

    const { result } = renderHook(() => useCreatePlannedWorkout(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        title: "Tempo run",
        scheduled_date: "2024-06-15",
        workout_type: "running",
      } as any);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockToast.success).toHaveBeenCalledWith("Workout planned");
  });

  it("shows error toast on failure", async () => {
    mockGarminApi.createPlannedWorkout.mockRejectedValueOnce(new Error("fail"));

    const { result } = renderHook(() => useCreatePlannedWorkout(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ title: "Run" } as any);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Failed to create planned workout");
  });
});

describe("useUpdatePlannedWorkout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates workout and shows toast", async () => {
    mockGarminApi.updatePlannedWorkout.mockResolvedValueOnce({ id: 1 });

    const { result } = renderHook(() => useUpdatePlannedWorkout(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ id: 1, body: { title: "Long run" } as any });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.updatePlannedWorkout).toHaveBeenCalledWith(1, { title: "Long run" });
    expect(mockToast.success).toHaveBeenCalledWith("Workout updated");
  });
});

describe("useDeletePlannedWorkout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("deletes workout and shows toast", async () => {
    mockGarminApi.deletePlannedWorkout.mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useDeletePlannedWorkout(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(42);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.deletePlannedWorkout).toHaveBeenCalledWith(42);
    expect(mockToast.success).toHaveBeenCalledWith("Workout deleted");
  });

  it("shows error toast on failure", async () => {
    mockGarminApi.deletePlannedWorkout.mockRejectedValueOnce(new Error("fail"));

    const { result } = renderHook(() => useDeletePlannedWorkout(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(42);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Failed to delete workout");
  });
});

describe("useImportPlannedWorkouts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("imports workouts with success toast", async () => {
    mockGarminApi.importPlannedWorkouts.mockResolvedValueOnce({
      imported: 5,
      errors: [],
    });

    const { result } = renderHook(() => useImportPlannedWorkouts(), {
      wrapper: createWrapper(),
    });

    const file = new File(["content"], "workouts.csv", { type: "text/csv" });

    act(() => {
      result.current.mutate(file);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.importPlannedWorkouts).toHaveBeenCalledWith(file);
    expect(mockToast.success).toHaveBeenCalledWith("Imported 5 workouts");
  });

  it("shows warning toast on partial import", async () => {
    mockGarminApi.importPlannedWorkouts.mockResolvedValueOnce({
      imported: 3,
      errors: ["Row 4: invalid date", "Row 7: missing title"],
    });

    const { result } = renderHook(() => useImportPlannedWorkouts(), {
      wrapper: createWrapper(),
    });

    const file = new File(["content"], "workouts.csv", { type: "text/csv" });

    act(() => {
      result.current.mutate(file);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockToast.warning).toHaveBeenCalledWith(
      "Imported 3 workouts with 2 errors"
    );
  });

  it("shows error toast on complete failure", async () => {
    mockGarminApi.importPlannedWorkouts.mockRejectedValueOnce(new Error("parse error"));

    const { result } = renderHook(() => useImportPlannedWorkouts(), {
      wrapper: createWrapper(),
    });

    const file = new File(["bad"], "workouts.csv", { type: "text/csv" });

    act(() => {
      result.current.mutate(file);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Failed to import workouts");
  });
});
