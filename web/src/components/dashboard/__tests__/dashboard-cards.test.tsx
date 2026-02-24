import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReadinessCard } from "../readiness-card";
import { WeeklySummary } from "../weekly-summary";
import { VmaCard } from "../vma-card";

// Mock all hooks that make API calls
vi.mock("@/hooks/use-metrics", () => ({
  useTrainingReadiness: vi.fn(),
  useSleep: vi.fn(),
  useBodyBattery: vi.fn(),
  useHrv: vi.fn(),
  useDailySummary: vi.fn(),
  useFitnessMetrics: vi.fn(),
  useBodyComposition: vi.fn(),
  useStress: vi.fn(),
}));

vi.mock("@/hooks/use-activities", () => ({
  useActivities: vi.fn(),
  useActivity: vi.fn(),
  useActivitySplits: vi.fn(),
  useUpdateActivity: vi.fn(),
}));

vi.mock("@/hooks/use-vma", () => ({
  useVma: vi.fn(),
  useUpdateVma: vi.fn(),
}));

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import {
  useTrainingReadiness,
  useSleep,
  useBodyBattery,
  useHrv,
} from "@/hooks/use-metrics";
import { useActivities } from "@/hooks/use-activities";
import { useVma, useUpdateVma } from "@/hooks/use-vma";

const mockUseTrainingReadiness = vi.mocked(useTrainingReadiness);
const mockUseSleep = vi.mocked(useSleep);
const mockUseBodyBattery = vi.mocked(useBodyBattery);
const mockUseHrv = vi.mocked(useHrv);
const mockUseActivities = vi.mocked(useActivities);
const mockUseVma = vi.mocked(useVma);
const mockUseUpdateVma = vi.mocked(useUpdateVma);

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

const emptyPage = {
  data: [],
  pagination: { total: 0, limit: 50, offset: 0, has_more: false },
};

function pendingMetricsState() {
  return { data: undefined, isPending: true, isError: false } as ReturnType<
    typeof useTrainingReadiness
  >;
}

function errorMetricsState() {
  return { data: undefined, isPending: false, isError: true } as ReturnType<
    typeof useTrainingReadiness
  >;
}

function successMetricsState<T>(data: T) {
  return { data, isPending: false, isError: false } as ReturnType<
    typeof useTrainingReadiness
  >;
}

// ---------------------------------------------------------------------------
// ReadinessCard
// ---------------------------------------------------------------------------

describe("ReadinessCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton while data is pending", () => {
    mockUseTrainingReadiness.mockReturnValue(pendingMetricsState());
    mockUseSleep.mockReturnValue(pendingMetricsState());
    mockUseBodyBattery.mockReturnValue(pendingMetricsState());
    mockUseHrv.mockReturnValue(pendingMetricsState());

    const { container } = render(<ReadinessCard />, {
      wrapper: createWrapper(),
    });
    // Score text should not appear during loading
    expect(container.querySelector("text")).toBeNull();
  });

  it("renders error state when all queries fail", () => {
    mockUseTrainingReadiness.mockReturnValue(errorMetricsState());
    mockUseSleep.mockReturnValue(errorMetricsState());
    mockUseBodyBattery.mockReturnValue(errorMetricsState());
    mockUseHrv.mockReturnValue(errorMetricsState());

    const { getAllByText } = render(<ReadinessCard />, { wrapper: createWrapper() });

    const errors = getAllByText(/could not load data/i);
    expect(errors.length).toBeGreaterThanOrEqual(1);
  });

  it("renders readiness score when data is available", () => {
    const trPage = {
      data: [{ calendar_date: "2026-02-24", score: 75, sleep_score: 80 }],
      pagination: { total: 1, limit: 1, offset: 0, has_more: false },
    };
    const sleepPage = {
      data: [{ calendar_date: "2026-02-24", sleep_score: 80 }],
      pagination: { total: 1, limit: 1, offset: 0, has_more: false },
    };
    const bbPage = {
      data: [{ calendar_date: "2026-02-24", highest_value: 85 }],
      pagination: { total: 1, limit: 1, offset: 0, has_more: false },
    };
    const hrvPage = {
      data: [{ calendar_date: "2026-02-24", weekly_avg: 55 }],
      pagination: { total: 1, limit: 1, offset: 0, has_more: false },
    };

    mockUseTrainingReadiness.mockReturnValue(successMetricsState(trPage));
    mockUseSleep.mockReturnValue(successMetricsState(sleepPage));
    mockUseBodyBattery.mockReturnValue(successMetricsState(bbPage));
    mockUseHrv.mockReturnValue(successMetricsState(hrvPage));

    render(<ReadinessCard />, { wrapper: createWrapper() });

    expect(screen.getByText("75")).toBeInTheDocument();
    expect(screen.getByText("Sleep Score")).toBeInTheDocument();
    expect(screen.getByText("Body Battery")).toBeInTheDocument();
    expect(screen.getByText("HRV")).toBeInTheDocument();
  });

  it("renders dash for missing metric values", () => {
    const trPage = {
      data: [{ calendar_date: "2026-02-24", score: null }],
      pagination: { total: 1, limit: 1, offset: 0, has_more: false },
    };

    mockUseTrainingReadiness.mockReturnValue(successMetricsState(trPage));
    mockUseSleep.mockReturnValue(successMetricsState(emptyPage));
    mockUseBodyBattery.mockReturnValue(successMetricsState(emptyPage));
    mockUseHrv.mockReturnValue(successMetricsState(emptyPage));

    render(<ReadinessCard />, { wrapper: createWrapper() });

    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// WeeklySummary
// ---------------------------------------------------------------------------

describe("WeeklySummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeletons while pending", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<WeeklySummary />, { wrapper: createWrapper() });

    expect(screen.queryByText(/this week runs/i)).not.toBeInTheDocument();
  });

  it("renders error message when activities fail", () => {
    mockUseActivities.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    } as ReturnType<typeof useActivities>);

    const { getAllByText } = render(<WeeklySummary />, {
      wrapper: createWrapper(),
    });

    const errors = getAllByText(/could not load data/i);
    expect(errors.length).toBeGreaterThanOrEqual(1);
  });

  it("renders zero stats with empty activities", () => {
    mockUseActivities.mockReturnValue({
      data: emptyPage,
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    const { getAllByText, container } = render(<WeeklySummary />, {
      wrapper: createWrapper(),
    });

    // Title appears in the rendered component
    const titles = getAllByText(/this week runs/i);
    expect(titles.length).toBeGreaterThanOrEqual(1);
    // Zero runs count
    expect(container.textContent).toContain("0");
  });

  it("renders activity stats with running activities", () => {
    const today = new Date();
    const todayStr = today.toISOString().slice(0, 10);

    const runningActivity = {
      activity_id: 1,
      activity_type: "running",
      start_timestamp: `${todayStr}T08:00:00Z`,
      duration_seconds: 3600,
      distance_meters: 10000,
      elevation_gain_meters: 200,
    };

    mockUseActivities.mockReturnValue({
      data: {
        data: [runningActivity],
        pagination: { total: 1, limit: 100, offset: 0, has_more: false },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    const { container, getAllByText } = render(<WeeklySummary />, {
      wrapper: createWrapper(),
    });

    const titles = getAllByText(/this week runs/i);
    expect(titles.length).toBeGreaterThanOrEqual(1);
    expect(container.textContent).toContain("Runs");
  });
});

// ---------------------------------------------------------------------------
// VmaCard
// ---------------------------------------------------------------------------

describe("VmaCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeleton while pending", () => {
    mockUseVma.mockReturnValue({
      data: undefined,
      isPending: true,
      isError: false,
    } as ReturnType<typeof useVma>);

    const { container } = render(<VmaCard />, { wrapper: createWrapper() });

    // VMA title not yet rendered
    expect(container.querySelector("[data-slot='card-title']")).toBeNull();
  });

  it("renders error state when query fails", () => {
    mockUseVma.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
    } as ReturnType<typeof useVma>);

    const { getAllByText } = render(<VmaCard />, { wrapper: createWrapper() });

    const errors = getAllByText(/could not load data/i);
    expect(errors.length).toBeGreaterThanOrEqual(1);
  });

  it("renders VMA value when data is available", () => {
    mockUseVma.mockReturnValue({
      data: { manual_vma: null, estimated_vma: 16.5, vo2_max: 55 },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useVma>);
    mockUseUpdateVma.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateVma>);

    render(<VmaCard />, { wrapper: createWrapper() });

    expect(screen.getByText("16.5 km/h")).toBeInTheDocument();
    expect(screen.getByText("estimated")).toBeInTheDocument();
  });

  it("renders manual badge when manual VMA is set", () => {
    mockUseVma.mockReturnValue({
      data: { manual_vma: 17.0, estimated_vma: 16.5, vo2_max: 55 },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useVma>);
    mockUseUpdateVma.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateVma>);

    render(<VmaCard />, { wrapper: createWrapper() });

    expect(screen.getByText("17 km/h")).toBeInTheDocument();
    expect(screen.getByText("manual")).toBeInTheDocument();
  });

  it("renders dash when no VMA data", () => {
    mockUseVma.mockReturnValue({
      data: { manual_vma: null, estimated_vma: null, vo2_max: null },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useVma>);
    mockUseUpdateVma.mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useUpdateVma>);

    const { getAllByText } = render(<VmaCard />, { wrapper: createWrapper() });

    // At least one dash shown for missing VMA
    const dashes = getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });
});
