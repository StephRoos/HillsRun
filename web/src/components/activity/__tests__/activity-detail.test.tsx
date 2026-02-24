import React from "react";
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityCard } from "../activity-card";
import { ActivityMetrics } from "../activity-metrics";
import { SplitsTable } from "../splits-table";
import type { Activity, ActivityDetail, ActivitySplit } from "@/types/garmin";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
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

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

const baseActivity: Activity = {
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
};

const detailActivity: ActivityDetail = {
  ...baseActivity,
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
  description: "Great morning trail run",
  manual_activity: false,
  pr: false,
  favorite: true,
};

// ---------------------------------------------------------------------------
// ActivityCard
// ---------------------------------------------------------------------------

describe("ActivityCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders activity name", () => {
    const { getByText } = render(<ActivityCard activity={baseActivity} />, {
      wrapper: createWrapper(),
    });
    expect(getByText("Morning Run")).toBeInTheDocument();
  });

  it("renders custom_name when set", () => {
    const activity = { ...baseActivity, custom_name: "Trail race warm-up" };
    const { getByText } = render(<ActivityCard activity={activity} />, {
      wrapper: createWrapper(),
    });
    expect(getByText("Trail race warm-up")).toBeInTheDocument();
  });

  it("renders activity type badge", () => {
    const { container } = render(<ActivityCard activity={baseActivity} />, {
      wrapper: createWrapper(),
    });
    // Badge is the first span with data-slot="badge"
    const badge = container.querySelector("[data-slot='badge']");
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toBeTruthy();
  });

  it("links to activity detail page", () => {
    const { container } = render(<ActivityCard activity={baseActivity} />, {
      wrapper: createWrapper(),
    });
    const link = container.querySelector("a");
    expect(link?.getAttribute("href")).toContain("42");
  });

  it("renders fallback when activity_name is null", () => {
    const activity = { ...baseActivity, activity_name: null, custom_name: null };
    const { getByText } = render(<ActivityCard activity={activity} />, {
      wrapper: createWrapper(),
    });
    expect(getByText("Activity")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ActivityMetrics
// ---------------------------------------------------------------------------

describe("ActivityMetrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all metric labels", () => {
    const { getByText } = render(<ActivityMetrics activity={detailActivity} />, {
      wrapper: createWrapper(),
    });

    expect(getByText("D+")).toBeInTheDocument();
    expect(getByText("D-")).toBeInTheDocument();
    expect(getByText("Duration")).toBeInTheDocument();
    expect(getByText("Avg pace")).toBeInTheDocument();
    expect(getByText("Avg / max HR")).toBeInTheDocument();
  });

  it("renders heart rate combined metric", () => {
    const { getAllByText } = render(
      <ActivityMetrics activity={detailActivity} />,
      { wrapper: createWrapper() }
    );
    // "160 / 185 bpm" may appear once (bold value in MetricCard)
    const hrValues = getAllByText("160 / 185 bpm");
    expect(hrValues.length).toBeGreaterThanOrEqual(1);
  });

  it("renders dash when heart rate is null", () => {
    const activity = { ...detailActivity, average_hr: null, max_hr: null };
    const { getAllByText } = render(<ActivityMetrics activity={activity} />, {
      wrapper: createWrapper(),
    });
    const dashes = getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// SplitsTable
// ---------------------------------------------------------------------------

describe("SplitsTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders nothing when splits array is empty", () => {
    const { container } = render(<SplitsTable splits={[]} />, {
      wrapper: createWrapper(),
    });
    expect(container.firstChild).toBeNull();
  });

  it("renders splits card title", () => {
    const splits: ActivitySplit[] = [
      {
        split_index: 0,
        split_type: "km",
        duration_seconds: 360,
        distance_meters: 1000,
        average_speed: 2.78,
        average_hr: 162,
        calories: 55,
        elevation_gain: 12,
      },
    ];
    const { getByText } = render(<SplitsTable splits={splits} />, {
      wrapper: createWrapper(),
    });

    expect(getByText("Splits")).toBeInTheDocument();
  });

  it("renders table header row", () => {
    const splits: ActivitySplit[] = [
      {
        split_index: 0,
        split_type: "km",
        duration_seconds: 360,
        distance_meters: 1000,
        average_speed: 2.78,
        average_hr: 162,
        calories: 55,
        elevation_gain: 12,
      },
    ];
    const { container } = render(<SplitsTable splits={splits} />, {
      wrapper: createWrapper(),
    });

    const table = container.querySelector("table");
    expect(table).not.toBeNull();
    const thead = table?.querySelector("thead");
    expect(thead?.textContent).toContain("#");
    expect(thead?.textContent).toContain("Duration");
  });

  it("renders heart rate in bpm for each split", () => {
    const splits: ActivitySplit[] = [
      {
        split_index: 0,
        split_type: "km",
        duration_seconds: 360,
        distance_meters: 1000,
        average_speed: 2.78,
        average_hr: 162,
        calories: 55,
        elevation_gain: 12,
      },
    ];
    const { container } = render(<SplitsTable splits={splits} />, {
      wrapper: createWrapper(),
    });
    // 162 bpm should appear in the table body
    const tbody = container.querySelector("tbody");
    expect(tbody?.textContent).toContain("162 bpm");
  });

  it("renders dash for null elevation gain and heart rate", () => {
    const splits: ActivitySplit[] = [
      {
        split_index: 0,
        split_type: "km",
        duration_seconds: 360,
        distance_meters: 1000,
        average_speed: 2.78,
        average_hr: null,
        calories: null,
        elevation_gain: null,
      },
    ];
    const { getAllByText } = render(<SplitsTable splits={splits} />, {
      wrapper: createWrapper(),
    });
    const dashes = getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(2);
  });

  it("renders multiple splits rows correctly", () => {
    const splits: ActivitySplit[] = [
      {
        split_index: 0,
        split_type: "km",
        duration_seconds: 360,
        distance_meters: 1000,
        average_speed: 2.78,
        average_hr: 160,
        calories: 55,
        elevation_gain: 10,
      },
      {
        split_index: 1,
        split_type: "km",
        duration_seconds: 355,
        distance_meters: 1000,
        average_speed: 2.82,
        average_hr: 165,
        calories: 54,
        elevation_gain: 5,
      },
    ];
    const { container } = render(<SplitsTable splits={splits} />, {
      wrapper: createWrapper(),
    });

    const rows = container.querySelectorAll("tbody tr");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain("160 bpm");
    expect(rows[1].textContent).toContain("165 bpm");
  });
});
