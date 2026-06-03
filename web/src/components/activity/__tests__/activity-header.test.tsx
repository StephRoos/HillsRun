import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityHeader } from "../activity-header";
import type { ActivityDetail } from "@/types/garmin";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
  }),
}));

vi.mock("@/hooks/use-activities", () => ({
  useActivities: vi.fn(),
  useActivity: vi.fn(),
  useActivitySplits: vi.fn(),
  useUpdateActivity: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    variables: undefined,
  })),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const baseActivity: ActivityDetail = {
  activity_id: 42,
  activity_name: "Morning Run",
  custom_name: null,
  activity_type: "running",
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
  average_power: null,
  max_power: null,
  normalized_power: null,
  intensity_factor: null,
  min_elevation_meters: 100,
  max_elevation_meters: 350,
  average_temperature: 12,
  max_temperature: 15,
  min_temperature: 9,
  training_effect: 3.5,
  avg_vertical_oscillation: 0.09,
  avg_ground_contact_time: 245,
  avg_stride_length: 1.35,
  lactate_threshold_bpm: 172,
  description: "Great trail run",
  manual_activity: false,
  pr: false,
  favorite: true,
};

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {component}
    </QueryClientProvider>
  );
};

describe("ActivityHeader", () => {
  it("renders activity name", () => {
    renderWithProviders(<ActivityHeader activity={baseActivity} />);
    expect(screen.getByText("Morning Run")).toBeInTheDocument();
  });

  it("renders custom_name when set", () => {
    const activityWithCustomName = {
      ...baseActivity,
      custom_name: "My Custom Name",
    };
    renderWithProviders(
      <ActivityHeader activity={activityWithCustomName} />
    );
    expect(screen.getByText("My Custom Name")).toBeInTheDocument();
  });

  it("renders Dashboard back button", () => {
    renderWithProviders(<ActivityHeader activity={baseActivity} />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("renders activity type badge", () => {
    renderWithProviders(<ActivityHeader activity={baseActivity} />);
    const badge = screen.getByText(/running/i);
    expect(badge).toBeInTheDocument();
  });

  it("shows PR badge when activity has PR", () => {
    const activityWithPR = {
      ...baseActivity,
      pr: true,
    };
    renderWithProviders(<ActivityHeader activity={activityWithPR} />);
    expect(screen.getByText("PR")).toBeInTheDocument();
  });

  it("shows Favorite badge when activity is favorite", () => {
    renderWithProviders(<ActivityHeader activity={baseActivity} />);
    expect(screen.getByText("Favorite")).toBeInTheDocument();
  });

  it("hides PR badge when activity has no PR", () => {
    const activityWithoutPR = {
      ...baseActivity,
      pr: false,
    };
    renderWithProviders(<ActivityHeader activity={activityWithoutPR} />);
    expect(screen.queryByText("PR")).not.toBeInTheDocument();
  });

  it("renders device name", () => {
    renderWithProviders(<ActivityHeader activity={baseActivity} />);
    expect(screen.getByText("Fenix 7")).toBeInTheDocument();
  });

  it("renders description", () => {
    renderWithProviders(<ActivityHeader activity={baseActivity} />);
    expect(screen.getByText("Great trail run")).toBeInTheDocument();
  });

  it("hides description when null", () => {
    const activityWithoutDescription = {
      ...baseActivity,
      description: null,
    };
    renderWithProviders(
      <ActivityHeader activity={activityWithoutDescription} />
    );
    expect(screen.queryByText("Great trail run")).not.toBeInTheDocument();
  });
});
