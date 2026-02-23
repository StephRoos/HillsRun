import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useTrends } from "../use-trends";
import * as garminApiModule from "@/lib/garmin-api";

vi.mock("@/lib/garmin-api");

const mockGarminApi = vi.mocked(garminApiModule.garminApi);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

const mockPageResponse = {
  data: [],
  pagination: { total: 0, limit: 200, offset: 0, has_more: false },
};

describe("useTrends", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with all metric hooks", () => {
    mockGarminApi.getActivities.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(true);
  });

  it("uses correct start_date param for different periods", async () => {
    mockGarminApi.getActivities.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    renderHook(() => useTrends("4w"), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(mockGarminApi.getActivities).toHaveBeenCalled();
    });

    const call = mockGarminApi.getActivities.mock.calls[0][0];
    expect(call?.start_date).toBeDefined();
    expect(typeof call?.start_date).toBe("string");
  });

  it("filters activities to running types only", async () => {
    // Use current date to ensure activities fall within the period
    const today = new Date();
    const recentDate = new Date(today);
    recentDate.setDate(today.getDate() - 5);
    const timestamp = recentDate.toISOString();

    const mockActivities = {
      data: [
        {
          activity_id: 1,
          activity_type: "running",
          start_timestamp: timestamp,
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
        {
          activity_id: 2,
          activity_type: "cycling",
          start_timestamp: timestamp,
          duration_seconds: 3600,
          distance_meters: 20000,
          elevation_gain_meters: 50,
          elevation_loss_meters: 50,
        },
        {
          activity_id: 3,
          activity_type: "trail_running",
          start_timestamp: timestamp,
          duration_seconds: 3600,
          distance_meters: 12000,
          elevation_gain_meters: 200,
          elevation_loss_meters: 200,
        },
      ],
      pagination: { total: 3, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockActivities);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    // Should only have running and trail_running
    expect(result.current.periodSummary.totalActivities).toBe(2);
  });

  it("aggregates activities by week", async () => {
    const today = new Date();
    const daysSinceMonday = today.getUTCDay() || 7;
    const lastMonday = new Date(today);
    lastMonday.setUTCDate(today.getUTCDate() - (daysSinceMonday - 1));

    const date1 = new Date(lastMonday);
    const date2 = new Date(lastMonday);
    date2.setUTCDate(date1.getUTCDate() + 1);

    const mockActivities = {
      data: [
        {
          activity_id: 1,
          activity_type: "running",
          start_timestamp: date1.toISOString(),
          duration_seconds: 1800,
          distance_meters: 5000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
        {
          activity_id: 2,
          activity_type: "running",
          start_timestamp: date2.toISOString(),
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 200,
          elevation_loss_meters: 200,
        },
      ],
      pagination: { total: 2, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockActivities);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    const weekData = result.current.weeklyData;
    const currentWeekData = weekData[weekData.length - 1];
    expect(currentWeekData.distance).toBe(15000);
    expect(currentWeekData.duration).toBe(5400);
    expect(currentWeekData.elevationGain).toBe(300);
    expect(currentWeekData.count).toBe(2);
  });

  it("includes zero-data weeks in weekly data", async () => {
    const today = new Date();
    const mockActivities = {
      data: [
        {
          activity_id: 1,
          activity_type: "running",
          start_timestamp: today.toISOString(),
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
      ],
      pagination: { total: 1, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockActivities);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    // Should have entries for all weeks in the period, including zeros
    expect(result.current.weeklyData.length).toBeGreaterThan(1);
    const zeroWeek = result.current.weeklyData.find(
      (w) => w.distance === 0 && w.count === 0
    );
    expect(zeroWeek).toBeDefined();
  });

  it("calculates weekly averages from aggregated data", async () => {
    const today = new Date();
    const mockActivities = {
      data: [
        {
          activity_id: 1,
          activity_type: "running",
          start_timestamp: today.toISOString(),
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
      ],
      pagination: { total: 1, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockActivities);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    // Should have calculated averages
    expect(result.current.weeklyAverages).toBeDefined();
    expect(result.current.weeklyAverages.distance).toBeGreaterThanOrEqual(0);
    expect(result.current.weeklyAverages.duration).toBeGreaterThanOrEqual(0);
  });

  it("computes period summary from filtered activities", async () => {
    const today = new Date();
    const daysBack = new Date(today);
    daysBack.setDate(today.getDate() - 5);

    const mockActivities = {
      data: [
        {
          activity_id: 1,
          activity_type: "running",
          start_timestamp: daysBack.toISOString(),
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
        {
          activity_id: 2,
          activity_type: "trail_running",
          start_timestamp: today.toISOString(),
          duration_seconds: 7200,
          distance_meters: 15000,
          elevation_gain_meters: 300,
          elevation_loss_meters: 300,
        },
      ],
      pagination: { total: 2, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockActivities);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    expect(result.current.periodSummary.totalDistance).toBe(25000);
    expect(result.current.periodSummary.totalDuration).toBe(10800);
    expect(result.current.periodSummary.totalElevation).toBe(400);
    expect(result.current.periodSummary.totalActivities).toBe(2);
  });

  it("includes metric data in result", async () => {
    const mockReadinessData = {
      data: [{ calendar_date: "2024-01-15", training_readiness_value: 75 }],
      pagination: { total: 1, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(
      mockReadinessData
    );
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    expect(result.current.readiness).toEqual(mockReadinessData.data);
  });

  it("returns week ticks for charting", async () => {
    mockGarminApi.getActivities.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    expect(result.current.weekTicks.length).toBeGreaterThan(0);
    expect(result.current.weekTicks[0]).toHaveProperty("monday");
    expect(result.current.weekTicks[0]).toHaveProperty("label");
    expect(result.current.weekTicks[0]).toHaveProperty("year");
    expect(result.current.weekTicks[0]).toHaveProperty("isYearStart");
  });

  it("excludes activities without start_timestamp", async () => {
    const today = new Date();
    const mockActivities = {
      data: [
        {
          activity_id: 1,
          activity_type: "running",
          start_timestamp: today.toISOString(),
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
        {
          activity_id: 2,
          activity_type: "running",
          start_timestamp: null,
          duration_seconds: 3600,
          distance_meters: 10000,
          elevation_gain_meters: 100,
          elevation_loss_meters: 100,
        },
      ],
      pagination: { total: 2, limit: 200, offset: 0, has_more: false },
    };

    mockGarminApi.getActivities.mockResolvedValueOnce(mockActivities);
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrends("4w"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    // Only 1 activity should be counted (the one without timestamp is ignored)
    expect(result.current.periodSummary.totalActivities).toBe(1);
  });
});
