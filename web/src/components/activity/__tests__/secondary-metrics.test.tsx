import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SecondaryMetrics } from "../secondary-metrics";
import type { ActivityDetail } from "@/types/garmin";

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

const fullActivity: ActivityDetail = {
  activity_id: 42,
  activity_name: "Trail Run",
  custom_name: null,
  activity_type: "trail_running",
  sport_type: "running",
  start_timestamp: "2026-02-24T07:00:00Z",
  duration_seconds: 3600,
  distance_meters: 10000,
  average_speed: 2.78,
  max_speed: 4.5,
  calories: 500,
  average_hr: 160,
  max_hr: 185,
  elevation_gain_meters: 150,
  elevation_loss_meters: 140,
  training_stress_score: 60,
  vo2_max_value: 55,
  device_name: "Fenix 7",
  num_laps: 1,
  aerobic_training_effect: 3.5,
  anaerobic_training_effect: 0.8,
  average_pace: 360,
  max_pace: 222,
  average_running_cadence: 180,
  max_running_cadence: 198,
  average_bike_cadence: null,
  max_bike_cadence: null,
  average_power: 250,
  max_power: 300,
  normalized_power: null,
  intensity_factor: null,
  min_elevation_meters: 100,
  max_elevation_meters: 350,
  average_temperature: 12.5,
  max_temperature: 15,
  min_temperature: 9,
  training_effect: 3.5,
  avg_vertical_oscillation: 9.2,
  avg_ground_contact_time: 245,
  avg_stride_length: 135,
  lactate_threshold_bpm: 172,
  description: null,
  manual_activity: false,
  pr: false,
  favorite: false,
};

describe("SecondaryMetrics", () => {
  it("renders nothing when all metrics are null", () => {
    const activity: ActivityDetail = {
      ...fullActivity,
      average_running_cadence: null,
      avg_vertical_oscillation: null,
      avg_ground_contact_time: null,
      avg_stride_length: null,
      average_power: null,
      aerobic_training_effect: null,
      anaerobic_training_effect: null,
      vo2_max_value: null,
      calories: null,
      min_elevation_meters: null,
      max_elevation_meters: null,
      average_temperature: null,
    };

    const { container } = render(<SecondaryMetrics activity={activity} />, {
      wrapper: createWrapper(),
    });

    expect(container.firstChild).toBeNull();
  });

  it("renders detailed metrics title when data exists", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Detailed metrics")).toBeInTheDocument();
  });

  it("renders cadence in spm", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("180 spm")).toBeInTheDocument();
  });

  it("renders vertical oscillation in cm", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("9.2 cm")).toBeInTheDocument();
  });

  it("renders ground contact time in ms", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("245 ms")).toBeInTheDocument();
  });

  it("renders stride length in meters", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("1.35 m")).toBeInTheDocument();
  });

  it("renders power in watts", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("250 W")).toBeInTheDocument();
  });

  it("renders training effects", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("3.5")).toBeInTheDocument();
  });

  it("renders altitude min/max", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("100 / 350 m")).toBeInTheDocument();
  });

  it("renders temperature", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("12.5°C")).toBeInTheDocument();
  });

  it("renders calories", () => {
    render(<SecondaryMetrics activity={fullActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("500 kcal")).toBeInTheDocument();
  });
});
