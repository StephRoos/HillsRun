import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  garminApi,
  GarminNotConnectedError,
  setViewAsAthlete,
} from "../garmin-api";

// Mock window.location and fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock window.location.origin
Object.defineProperty(window, "location", {
  value: { origin: "http://localhost:3000" },
  writable: true,
});

describe("GarminNotConnectedError", () => {
  it("creates error with correct name and message", () => {
    const error = new GarminNotConnectedError();
    expect(error.name).toBe("GarminNotConnectedError");
    expect(error.message).toBe("Garmin account not connected");
  });

  it("is an instance of Error", () => {
    const error = new GarminNotConnectedError();
    expect(error).toBeInstanceOf(Error);
  });
});

describe("garminApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setViewAsAthlete(null);
  });

  afterEach(() => {
    setViewAsAthlete(null);
  });

  describe("activities", () => {
    it("getActivities calls correct endpoint", async () => {
      const mockData = {
        data: [
          {
            activity_id: 1,
            activity_name: "Morning run",
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
          },
        ],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await garminApi.getActivities({ limit: "50" });
      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/activities?limit=50"),
        expect.any(Object)
      );
    });

    it("getActivity calls correct endpoint with id", async () => {
      const mockData = {
        activity_id: 1,
        activity_name: "Morning run",
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await garminApi.getActivity("123");
      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/activities/123"),
        expect.any(Object)
      );
    });

    it("getActivitySplits calls correct endpoint", async () => {
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await garminApi.getActivitySplits("123");
      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/activities/123/splits"),
        expect.any(Object)
      );
    });
  });

  describe("daily health", () => {
    it("getDailySummary calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getDailySummary();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/daily/summary"),
        expect.any(Object)
      );
    });

    it("getSleep calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getSleep();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/daily/sleep"),
        expect.any(Object)
      );
    });

    it("getBodyBattery calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getBodyBattery();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/daily/body-battery"),
        expect.any(Object)
      );
    });

    it("getStress calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getStress();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/daily/stress"),
        expect.any(Object)
      );
    });
  });

  describe("advanced metrics", () => {
    it("getHrv calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getHrv();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/metrics/hrv"),
        expect.any(Object)
      );
    });

    it("getTrainingReadiness calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getTrainingReadiness();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/metrics/training-readiness"),
        expect.any(Object)
      );
    });

    it("getFitnessMetrics calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getFitnessMetrics();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/metrics/fitness"),
        expect.any(Object)
      );
    });
  });

  describe("body", () => {
    it("getBodyComposition calls correct endpoint", async () => {
      const mockData = {
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      await garminApi.getBodyComposition();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/body/composition"),
        expect.any(Object)
      );
    });
  });

  describe("error handling", () => {
    it("throws GarminNotConnectedError on 403", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({}),
      });

      await expect(garminApi.getActivities()).rejects.toThrow(
        GarminNotConnectedError
      );
    });

    it("throws Error on other status codes", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: "Internal server error" }),
      });

      await expect(garminApi.getActivities()).rejects.toThrow(
        "Internal server error"
      );
    });

    it("uses detail field from error response", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ detail: "Bad request" }),
      });

      await expect(garminApi.getActivities()).rejects.toThrow("Bad request");
    });

    it("uses status code as fallback error message", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => {
          throw new Error("Not JSON");
        },
      });

      await expect(garminApi.getActivities()).rejects.toThrow(
        /Garmin API error: 400/
      );
    });
  });

  describe("view as athlete", () => {
    it("includes X-View-As-Athlete header when set", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: [],
          pagination: { total: 0, limit: 50, offset: 0, has_more: false },
        }),
      });

      setViewAsAthlete(42);
      await garminApi.getActivities();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-View-As-Athlete": "42",
          }),
        })
      );
    });

    it("does not include X-View-As-Athlete header when null", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: [],
          pagination: { total: 0, limit: 50, offset: 0, has_more: false },
        }),
      });

      setViewAsAthlete(null);
      await garminApi.getActivities();

      const call = mockFetch.mock.calls[0];
      expect(call[1]?.headers).not.toHaveProperty("X-View-As-Athlete");
    });
  });

  describe("updateActivity", () => {
    it("sends PATCH request with custom_name", async () => {
      const mockData = {
        activity_id: 1,
        activity_name: "Morning run",
        custom_name: "My favorite run",
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

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await garminApi.updateActivity("123", {
        custom_name: "My favorite run",
      });

      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/activities/123"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ custom_name: "My favorite run" }),
        })
      );
    });
  });

  describe("sync", () => {
    it("triggerSync sends POST request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: "job-123" }),
      });

      const result = await garminApi.triggerSync({ mode: "full" });

      expect(result).toEqual({ job_id: "job-123" });
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/sync/trigger"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ mode: "full" }),
        })
      );
    });

    it("triggerSync handles 409 as success", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({}),
      });

      await expect(garminApi.triggerSync()).resolves.toBeDefined();
    });

    it("getSyncStatus calls correct endpoint", async () => {
      const mockData = { running: false };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await garminApi.getSyncStatus();

      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/sync/status"),
        expect.any(Object)
      );
    });

    it("getSyncJob calls correct endpoint with jobId", async () => {
      const mockData = { status: "completed", error: null };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await garminApi.getSyncJob("job-123");

      expect(result).toEqual(mockData);
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/sync/jobs/job-123"),
        expect.any(Object)
      );
    });
  });

  describe("planned workouts", () => {
    it("getPlannedWorkouts calls correct endpoint", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: [],
          pagination: { total: 0, limit: 50, offset: 0, has_more: false },
        }),
      });

      await garminApi.getPlannedWorkouts();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/planned-workouts"),
        expect.any(Object)
      );
    });

    it("getPlannedWorkout calls correct endpoint with id", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, description: "Workout" }),
      });

      await garminApi.getPlannedWorkout(1);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/planned-workouts/1"),
        expect.any(Object)
      );
    });

    it("createPlannedWorkout sends POST request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, description: "New workout" }),
      });

      await garminApi.createPlannedWorkout({
        description: "New workout",
        date: "2024-01-01",
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/planned-workouts"),
        expect.objectContaining({
          method: "POST",
        })
      );
    });

    it("updatePlannedWorkout sends PATCH request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 1, description: "Updated workout" }),
      });

      await garminApi.updatePlannedWorkout(1, {
        description: "Updated workout",
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/planned-workouts/1"),
        expect.objectContaining({
          method: "PATCH",
        })
      );
    });

    it("deletePlannedWorkout sends DELETE request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await garminApi.deletePlannedWorkout(1);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/planned-workouts/1"),
        expect.objectContaining({
          method: "DELETE",
        })
      );
    });
  });

  describe("user profile", () => {
    it("getVma calls correct endpoint", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ vma: 16.5 }),
      });

      await garminApi.getVma();

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/user/vma"),
        expect.any(Object)
      );
    });

    it("updateVma sends PATCH request", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ vma: 17.0 }),
      });

      await garminApi.updateVma(17.0);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/user/vma"),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ vma: 17.0 }),
        })
      );
    });

    it("updateVma handles null vma", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ vma: null }),
      });

      await garminApi.updateVma(null);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/user/vma"),
        expect.objectContaining({
          body: JSON.stringify({ vma: null }),
        })
      );
    });
  });

  describe("importPlannedWorkouts", () => {
    it("imports file with FormData", async () => {
      const file = new File(["content"], "workouts.csv", {
        type: "text/csv",
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ imported: 5, skipped: 0, errors: [] }),
      });

      await garminApi.importPlannedWorkouts(file);

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/garmin/planned-workouts/import"),
        expect.objectContaining({
          method: "POST",
        })
      );
    });
  });
});
