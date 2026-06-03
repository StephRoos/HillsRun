import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ActivityList } from "../activity-list";

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

vi.mock("../activity-card", () => ({
  ActivityCard: ({ activity }: { activity: Activity }) => (
    <div data-testid={`activity-card-${activity.activity_id}`}>
      {activity.activity_name}
    </div>
  ),
}));

import { useActivities } from "@/hooks/use-activities";

const mockUseActivities = vi.mocked(useActivities);

type Activity = {
  activity_id: number;
  activity_name: string;
  custom_name: string | null;
  activity_type: string;
  sport_type: string;
  start_timestamp: string;
  duration_seconds: number;
  distance_meters: number;
  average_speed: number;
  max_speed: number;
  calories: number;
  average_hr: number;
  max_hr: number;
  elevation_gain_meters: number;
  elevation_loss_meters: number;
  training_stress_score: number;
  vo2_max_value: number;
  device_name: string;
  num_laps: number;
  aerobic_training_effect: number;
  anaerobic_training_effect: number;
};

const mockActivity: Activity = {
  activity_id: 1,
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

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
  Wrapper.displayName = "TestQueryWrapper";
  return Wrapper;
};

describe("ActivityList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders loading skeletons when pending", () => {
    mockUseActivities.mockReturnValue({
      data: { data: [] },
      isPending: true,
      isError: false,
      isSuccess: false,
      isFetching: false,
      dataUpdatedAt: Date.now(),
      error: null,
      failureCount: 0,
      failureReason: null,
      status: "pending",
    } as unknown as ReturnType<typeof useActivities>);

    const { container } = render(<ActivityList />, { wrapper: createWrapper() });
    const skeletons = container.querySelectorAll("[data-slot='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders error message when activities fail", () => {
    mockUseActivities.mockReturnValue({
      data: { data: [] },
      isPending: false,
      isError: true,
      isSuccess: false,
      isFetching: false,
      dataUpdatedAt: Date.now(),
      error: new Error("Failed to load activities"),
      failureCount: 1,
      failureReason: new Error("Failed to load activities"),
      status: "error",
    } as unknown as ReturnType<typeof useActivities>);

    render(<ActivityList />, { wrapper: createWrapper() });

    expect(screen.getByText("Error loading activities.")).toBeInTheDocument();
  });

  it("renders no activities found when data is empty", () => {
    mockUseActivities.mockReturnValue({
      data: { data: [] },
      isPending: false,
      isError: false,
      isSuccess: true,
      isFetching: false,
      dataUpdatedAt: Date.now(),
      error: null,
      failureCount: 0,
      failureReason: null,
      status: "success",
    } as unknown as ReturnType<typeof useActivities>);

    render(<ActivityList />, { wrapper: createWrapper() });

    expect(screen.getByText("No activities found.")).toBeInTheDocument();
  });

  it("renders activity cards for each activity", () => {
    const mockActivities: Activity[] = [
      mockActivity,
      {
        ...mockActivity,
        activity_id: 2,
        activity_name: "Trail Run",
        activity_type: "trail",
        distance_meters: 15000,
      },
      {
        ...mockActivity,
        activity_id: 3,
        activity_name: "Strength Session",
        activity_type: "strength",
        distance_meters: 0,
      },
    ];

    mockUseActivities.mockReturnValue({
      data: { data: mockActivities },
      isPending: false,
      isError: false,
      isSuccess: true,
      isFetching: false,
      dataUpdatedAt: Date.now(),
      error: null,
      failureCount: 0,
      failureReason: null,
      status: "success",
    } as unknown as ReturnType<typeof useActivities>);

    render(<ActivityList />, { wrapper: createWrapper() });

    expect(screen.getByTestId("activity-card-1")).toBeInTheDocument();
    expect(screen.getByTestId("activity-card-2")).toBeInTheDocument();
    expect(screen.getByTestId("activity-card-3")).toBeInTheDocument();
    expect(screen.getByText("Morning Run")).toBeInTheDocument();
    expect(screen.getByText("Trail Run")).toBeInTheDocument();
    expect(screen.getByText("Strength Session")).toBeInTheDocument();
  });

  it("renders filter buttons", () => {
    mockUseActivities.mockReturnValue({
      data: { data: [] },
      isPending: false,
      isError: false,
      isSuccess: true,
      isFetching: false,
      dataUpdatedAt: Date.now(),
      error: null,
      failureCount: 0,
      failureReason: null,
      status: "success",
    } as unknown as ReturnType<typeof useActivities>);

    render(<ActivityList />, { wrapper: createWrapper() });

    expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /running/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /trail/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /strength/i })).toBeInTheDocument();
  });

  it("changes filter on button click", async () => {
    const user = userEvent.setup();

    mockUseActivities.mockReturnValue({
      data: { data: [mockActivity] },
      isPending: false,
      isError: false,
      isSuccess: true,
      isFetching: false,
      dataUpdatedAt: Date.now(),
      error: null,
      failureCount: 0,
      failureReason: null,
      status: "success",
    } as unknown as ReturnType<typeof useActivities>);

    render(<ActivityList />, { wrapper: createWrapper() });

    const runningButton = screen.getByRole("button", { name: /running/i });
    await user.click(runningButton);

    expect(mockUseActivities).toHaveBeenCalledWith(
      expect.objectContaining({
        activity_type: "running",
        limit: 20,
      })
    );
  });
});
