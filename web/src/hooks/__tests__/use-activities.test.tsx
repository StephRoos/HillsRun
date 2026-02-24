import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useActivities, useActivity, useActivitySplits, useUpdateActivity } from "../use-activities";
import * as garminApiModule from "@/lib/garmin-api";

vi.mock("@/lib/garmin-api");
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

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

describe("useActivities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches activities with default params", async () => {
    const mockData = {
      data: [],
      pagination: { total: 0, limit: 50, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useActivities(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(true);

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    expect(result.current.data).toEqual(mockData);
  });

  it("passes params to API call", async () => {
    const mockData = {
      data: [],
      pagination: { total: 0, limit: 10, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockData);

    const { result } = renderHook(
      () => useActivities({ limit: 10, offset: 20, activity_type: "running" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.getActivities).toHaveBeenCalledWith({
      limit: "10",
      offset: "20",
      activity_type: "running",
    });
  });

  it("includes date range in query params", async () => {
    const mockData = {
      data: [],
      pagination: { total: 0, limit: 50, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockData);

    const { result } = renderHook(
      () => useActivities({ start_date: "2024-01-01", end_date: "2024-01-31" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.getActivities).toHaveBeenCalledWith({
      start_date: "2024-01-01",
      end_date: "2024-01-31",
    });
  });

  it("builds query key from params", async () => {
    const mockData = {
      data: [],
      pagination: { total: 0, limit: 50, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockData);

    const { result } = renderHook(
      () => useActivities({ limit: 10, offset: 5 }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.getActivities).toHaveBeenCalledWith({
      limit: "10",
      offset: "5",
    });
  });
});

describe("useActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches single activity by id", async () => {
    const mockData = {
      activity_id: 1,
      activity_name: "Run",
      custom_name: null,
      activity_type: "running",
      sport_type: null,
      start_timestamp: "2024-01-01T08:00:00Z",
      duration_seconds: 3600,
      distance_meters: 10000,
      average_speed: 2.78,
      max_speed: 4.5,
      calories: 500,
      average_hr: 160,
      max_hr: 180,
      elevation_gain_meters: 100,
      elevation_loss_meters: 100,
      training_stress_score: 50,
      vo2_max_value: 55,
      device_name: "Garmin",
      num_laps: 1,
      aerobic_training_effect: 3.5,
      anaerobic_training_effect: 0,
      average_pace: 360,
      max_pace: 222,
      average_running_cadence: 180,
      max_running_cadence: 200,
      average_bike_cadence: null,
      max_bike_cadence: null,
      average_power: null,
      max_power: null,
      normalized_power: null,
      intensity_factor: null,
      min_elevation_meters: 100,
      max_elevation_meters: 200,
      average_temperature: 15,
      max_temperature: 20,
      min_temperature: 10,
      training_effect: 3.5,
      avg_vertical_oscillation: 0.1,
      avg_ground_contact_time: 250,
      avg_stride_length: 1.3,
      lactate_threshold_bpm: 170,
      description: "Great run",
      manual_activity: false,
      pr: false,
      favorite: false,
    };

    mockGarminApi.getActivity.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useActivity("123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockData);
    expect(mockGarminApi.getActivity).toHaveBeenCalledWith("123");
  });

  it("is disabled when id is empty", () => {
    const { result } = renderHook(() => useActivity(""), {
      wrapper: createWrapper(),
    });

    expect(mockGarminApi.getActivity).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("refetches when id changes", async () => {
    const mockData1 = { activity_id: 1 };
    const mockData2 = { activity_id: 2 };

    mockGarminApi.getActivity
      .mockResolvedValueOnce(mockData1)
      .mockResolvedValueOnce(mockData2);

    const { result, rerender } = renderHook(
      ({ id }) => useActivity(id),
      { wrapper: createWrapper(), initialProps: { id: "123" } }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    rerender({ id: "456" });

    await waitFor(() => {
      expect(mockGarminApi.getActivity).toHaveBeenCalledTimes(2);
    });
  });
});

describe("useActivitySplits", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches activity splits by id", async () => {
    const mockData = {
      data: [
        {
          split_index: 1,
          split_type: "km",
          duration_seconds: 360,
          distance_meters: 1000,
          average_speed: 2.78,
          average_hr: 160,
          calories: 50,
          elevation_gain: 10,
        },
      ],
      pagination: { total: 1, limit: 50, offset: 0, has_more: false },
    };

    mockGarminApi.getActivitySplits.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useActivitySplits("123"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockData);
    expect(mockGarminApi.getActivitySplits).toHaveBeenCalledWith("123");
  });

  it("is disabled when id is empty", () => {
    const { result } = renderHook(() => useActivitySplits(""), {
      wrapper: createWrapper(),
    });

    expect(mockGarminApi.getActivitySplits).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useUpdateActivity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends update request with custom name", async () => {
    const mockData = {
      activity_id: 1,
      activity_name: "Run",
      custom_name: "New name",
      activity_type: "running",
      sport_type: null,
      start_timestamp: "2024-01-01T08:00:00Z",
      duration_seconds: 3600,
      distance_meters: 10000,
      average_speed: 2.78,
      max_speed: 4.5,
      calories: 500,
      average_hr: 160,
      max_hr: 180,
      elevation_gain_meters: 100,
      elevation_loss_meters: 100,
      training_stress_score: 50,
      vo2_max_value: 55,
      device_name: "Garmin",
      num_laps: 1,
      aerobic_training_effect: 3.5,
      anaerobic_training_effect: 0,
      average_pace: 360,
      max_pace: 222,
      average_running_cadence: 180,
      max_running_cadence: 200,
      average_bike_cadence: null,
      max_bike_cadence: null,
      average_power: null,
      max_power: null,
      normalized_power: null,
      intensity_factor: null,
      min_elevation_meters: 100,
      max_elevation_meters: 200,
      average_temperature: 15,
      max_temperature: 20,
      min_temperature: 10,
      training_effect: 3.5,
      avg_vertical_oscillation: 0.1,
      avg_ground_contact_time: 250,
      avg_stride_length: 1.3,
      lactate_threshold_bpm: 170,
      description: "Great run",
      manual_activity: false,
      pr: false,
      favorite: false,
    };

    mockGarminApi.updateActivity.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useUpdateActivity("123"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(false);

    result.current.mutate({ custom_name: "New name" });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.updateActivity).toHaveBeenCalledWith("123", {
      custom_name: "New name",
    });
  });

  it("invalidates related queries on success", async () => {
    const mockData = {
      activity_id: 1,
      custom_name: "New",
      activity_type: "running",
      sport_type: null,
      activity_name: "Run",
      start_timestamp: "2024-01-01T08:00:00Z",
      duration_seconds: 3600,
      distance_meters: 10000,
      average_speed: 2.78,
      max_speed: 4.5,
      calories: 500,
      average_hr: 160,
      max_hr: 180,
      elevation_gain_meters: 100,
      elevation_loss_meters: 100,
      training_stress_score: 50,
      vo2_max_value: 55,
      device_name: "Garmin",
      num_laps: 1,
      aerobic_training_effect: 3.5,
      anaerobic_training_effect: 0,
      average_pace: 360,
      max_pace: 222,
      average_running_cadence: 180,
      max_running_cadence: 200,
      average_bike_cadence: null,
      max_bike_cadence: null,
      average_power: null,
      max_power: null,
      normalized_power: null,
      intensity_factor: null,
      min_elevation_meters: 100,
      max_elevation_meters: 200,
      average_temperature: 15,
      max_temperature: 20,
      min_temperature: 10,
      training_effect: 3.5,
      avg_vertical_oscillation: 0.1,
      avg_ground_contact_time: 250,
      avg_stride_length: 1.3,
      lactate_threshold_bpm: 170,
      description: "Great run",
      manual_activity: false,
      pr: false,
      favorite: false,
    };

    mockGarminApi.updateActivity.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useUpdateActivity("123"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ custom_name: "New" });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("handles null custom_name", async () => {
    const mockData = {
      activity_id: 1,
      activity_name: "Run",
      custom_name: null,
      activity_type: "running",
      sport_type: null,
      start_timestamp: "2024-01-01T08:00:00Z",
      duration_seconds: 3600,
      distance_meters: 10000,
      average_speed: 2.78,
      max_speed: 4.5,
      calories: 500,
      average_hr: 160,
      max_hr: 180,
      elevation_gain_meters: 100,
      elevation_loss_meters: 100,
      training_stress_score: 50,
      vo2_max_value: 55,
      device_name: "Garmin",
      num_laps: 1,
      aerobic_training_effect: 3.5,
      anaerobic_training_effect: 0,
      average_pace: 360,
      max_pace: 222,
      average_running_cadence: 180,
      max_running_cadence: 200,
      average_bike_cadence: null,
      max_bike_cadence: null,
      average_power: null,
      max_power: null,
      normalized_power: null,
      intensity_factor: null,
      min_elevation_meters: 100,
      max_elevation_meters: 200,
      average_temperature: 15,
      max_temperature: 20,
      min_temperature: 10,
      training_effect: 3.5,
      avg_vertical_oscillation: 0.1,
      avg_ground_contact_time: 250,
      avg_stride_length: 1.3,
      lactate_threshold_bpm: 170,
      description: "Great run",
      manual_activity: false,
      pr: false,
      favorite: false,
    };

    mockGarminApi.updateActivity.mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useUpdateActivity("123"), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ custom_name: null });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.updateActivity).toHaveBeenCalledWith("123", {
      custom_name: null,
    });
  });
});
