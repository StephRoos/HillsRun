import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TodayActivities } from "../today-activities";

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

describe("TodayActivities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders no activities message when data is empty", () => {
    mockUseActivities.mockReturnValue({
      data: emptyPage,
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<TodayActivities />, { wrapper: createWrapper() });

    expect(screen.getByText("No activities yet")).toBeInTheDocument();
  });

  it("renders no activities message when all activities are from other days", () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const yesterdayStr = yesterday.toISOString().slice(0, 10);

    mockUseActivities.mockReturnValue({
      data: {
        data: [
          {
            activity_id: 1,
            activity_type: "running",
            start_timestamp: `${yesterdayStr}T08:00:00Z`,
            duration_seconds: 3600,
            distance_meters: 10000,
            activity_name: "Morning Run",
            custom_name: null,
          },
        ],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<TodayActivities />, { wrapper: createWrapper() });

    expect(screen.getByText("No activities yet")).toBeInTheDocument();
  });

  it("renders today activities with name and distance", () => {
    const today = new Date().toISOString().slice(0, 10);

    mockUseActivities.mockReturnValue({
      data: {
        data: [
          {
            activity_id: 1,
            activity_type: "running",
            start_timestamp: `${today}T08:00:00Z`,
            duration_seconds: 3600,
            distance_meters: 10000,
            activity_name: "Morning Run",
            custom_name: null,
          },
        ],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<TodayActivities />, { wrapper: createWrapper() });

    expect(screen.getByText("Morning Run")).toBeInTheDocument();
    expect(screen.getByText("10.0 km")).toBeInTheDocument();
  });

  it("renders custom_name over activity_name", () => {
    const today = new Date().toISOString().slice(0, 10);

    mockUseActivities.mockReturnValue({
      data: {
        data: [
          {
            activity_id: 1,
            activity_type: "running",
            start_timestamp: `${today}T08:00:00Z`,
            duration_seconds: 3600,
            distance_meters: 5000,
            activity_name: "Morning Run",
            custom_name: "Speed Work",
          },
        ],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<TodayActivities />, { wrapper: createWrapper() });

    expect(screen.getByText("Speed Work")).toBeInTheDocument();
    expect(screen.queryByText("Morning Run")).not.toBeInTheDocument();
    expect(screen.getByText("5.0 km")).toBeInTheDocument();
  });

  it("renders activity_type as fallback when both names are null", () => {
    const today = new Date().toISOString().slice(0, 10);

    mockUseActivities.mockReturnValue({
      data: {
        data: [
          {
            activity_id: 1,
            activity_type: "trail_running",
            start_timestamp: `${today}T14:00:00Z`,
            duration_seconds: 5400,
            distance_meters: 12000,
            activity_name: null,
            custom_name: null,
          },
        ],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<TodayActivities />, { wrapper: createWrapper() });

    expect(screen.getByText("trail_running")).toBeInTheDocument();
    expect(screen.getByText("12.0 km")).toBeInTheDocument();
  });

  it("omits distance when distance_meters is null", () => {
    const today = new Date().toISOString().slice(0, 10);

    mockUseActivities.mockReturnValue({
      data: {
        data: [
          {
            activity_id: 1,
            activity_type: "running",
            start_timestamp: `${today}T10:00:00Z`,
            duration_seconds: 1800,
            distance_meters: null,
            activity_name: "Recovery Run",
            custom_name: null,
          },
        ],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
      },
      isPending: false,
      isError: false,
    } as ReturnType<typeof useActivities>);

    render(<TodayActivities />, { wrapper: createWrapper() });

    expect(screen.getByText("Recovery Run")).toBeInTheDocument();
    expect(screen.queryByText(/km/)).not.toBeInTheDocument();
  });
});
