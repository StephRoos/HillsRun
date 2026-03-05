import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SimilarActivities } from "../similar-activities";
import type { ActivityDetail } from "@/types/garmin";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/hooks/use-activities", () => ({
  useActivities: vi.fn(),
  useActivity: vi.fn(),
  useActivitySplits: vi.fn(),
  useUpdateActivity: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { useActivities } from "@/hooks/use-activities";

const mockUseActivities = vi.mocked(useActivities);

function createWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  return Wrapper;
}

const baseActivity: ActivityDetail = {
  activity_id: 1,
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

function mockActivitiesData(data: unknown[]) {
  mockUseActivities.mockReturnValue({
    data: { data },
    isPending: false,
    isError: false,
  } as ReturnType<typeof useActivities>);
}

describe("SimilarActivities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when activity has no distance", () => {
    mockActivitiesData([]);
    const activity = { ...baseActivity, distance_meters: null };

    const { container } = render(<SimilarActivities activity={activity} />, {
      wrapper: createWrapper(),
    });

    expect(container.firstChild).toBeNull();
  });

  it("returns null when no similar activities", () => {
    mockActivitiesData([
      { ...baseActivity, activity_id: 2, distance_meters: 20000 },
      { ...baseActivity, activity_id: 3, distance_meters: 5000 },
    ]);

    const { container } = render(<SimilarActivities activity={baseActivity} />, {
      wrapper: createWrapper(),
    });

    expect(container.firstChild).toBeNull();
  });

  it("renders similar activities within 20% distance", () => {
    const similarActivity = {
      ...baseActivity,
      activity_id: 2,
      distance_meters: 10500,
      start_timestamp: "2026-02-25T07:00:00Z",
    };
    mockActivitiesData([similarActivity]);

    render(<SimilarActivities activity={baseActivity} />, {
      wrapper: createWrapper(),
    });

    expect(screen.getByText("Similar activities")).toBeInTheDocument();
    expect(screen.getByText("Trail Run")).toBeInTheDocument();
  });

  it("limits to 5 similar activities", () => {
    const similarActivities = Array.from({ length: 7 }, (_, i) => ({
      ...baseActivity,
      activity_id: i + 2,
      distance_meters: 10200 + i * 100,
      start_timestamp: `2026-02-${String(25 + i).padStart(2, "0")}T07:00:00Z`,
    }));
    mockActivitiesData(similarActivities);

    render(<SimilarActivities activity={baseActivity} />, {
      wrapper: createWrapper(),
    });

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(5);
  });

  it("excludes current activity from similar list", () => {
    mockActivitiesData([
      baseActivity,
      {
        ...baseActivity,
        activity_id: 2,
        distance_meters: 10200,
        start_timestamp: "2026-02-25T07:00:00Z",
      },
    ]);

    render(<SimilarActivities activity={baseActivity} />, {
      wrapper: createWrapper(),
    });

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/activity/2");
  });

  it("renders activity links with correct href", () => {
    mockActivitiesData([
      {
        ...baseActivity,
        activity_id: 5,
        distance_meters: 10300,
        start_timestamp: "2026-02-25T07:00:00Z",
      },
    ]);

    render(<SimilarActivities activity={baseActivity} />, {
      wrapper: createWrapper(),
    });

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/activity/5");
  });
});
