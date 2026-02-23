import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useTrainingReadiness,
  useHrv,
  useFitnessMetrics,
  useDailySummary,
  useSleep,
  useBodyBattery,
  useBodyComposition,
  useStress,
} from "../use-metrics";
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
  pagination: { total: 0, limit: 50, offset: 0, has_more: false },
};

describe("useTrainingReadiness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches training readiness data", async () => {
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useTrainingReadiness(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes date range params to API", async () => {
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () =>
        useTrainingReadiness({
          start_date: "2024-01-01",
          end_date: "2024-01-31",
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getTrainingReadiness).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
      });
    });
  });

  it("passes limit param to API", async () => {
    mockGarminApi.getTrainingReadiness.mockResolvedValueOnce(mockPageResponse);

    renderHook(() => useTrainingReadiness({ limit: 100 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockGarminApi.getTrainingReadiness).toHaveBeenCalledWith({
        limit: "100",
      });
    });
  });
});

describe("useHrv", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches HRV data", async () => {
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useHrv(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes params to API", async () => {
    mockGarminApi.getHrv.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () =>
        useHrv({
          start_date: "2024-01-01",
          end_date: "2024-01-31",
          limit: 200,
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getHrv).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
        limit: "200",
      });
    });
  });
});

describe("useFitnessMetrics", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches fitness metrics", async () => {
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useFitnessMetrics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes all params to API", async () => {
    mockGarminApi.getFitnessMetrics.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () =>
        useFitnessMetrics({
          start_date: "2024-01-01",
          end_date: "2024-01-31",
          limit: 150,
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getFitnessMetrics).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
        limit: "150",
      });
    });
  });
});

describe("useDailySummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches daily summary", async () => {
    mockGarminApi.getDailySummary.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useDailySummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes start_date param", async () => {
    mockGarminApi.getDailySummary.mockResolvedValueOnce(mockPageResponse);

    renderHook(() => useDailySummary({ start_date: "2024-01-01" }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockGarminApi.getDailySummary).toHaveBeenCalledWith({
        start_date: "2024-01-01",
      });
    });
  });
});

describe("useSleep", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches sleep data", async () => {
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useSleep(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes date range params", async () => {
    mockGarminApi.getSleep.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () => useSleep({ start_date: "2024-01-01", end_date: "2024-01-31" }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getSleep).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
      });
    });
  });
});

describe("useBodyBattery", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches body battery data", async () => {
    mockGarminApi.getBodyBattery.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useBodyBattery(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes all params", async () => {
    mockGarminApi.getBodyBattery.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () =>
        useBodyBattery({
          start_date: "2024-01-01",
          end_date: "2024-01-31",
          limit: 50,
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getBodyBattery).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
        limit: "50",
      });
    });
  });
});

describe("useBodyComposition", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches body composition data", async () => {
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useBodyComposition(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes date params", async () => {
    mockGarminApi.getBodyComposition.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () =>
        useBodyComposition({
          start_date: "2024-01-01",
          end_date: "2024-01-31",
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getBodyComposition).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
      });
    });
  });
});

describe("useStress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches stress data", async () => {
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    const { result } = renderHook(() => useStress(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockPageResponse);
  });

  it("passes all params", async () => {
    mockGarminApi.getStress.mockResolvedValueOnce(mockPageResponse);

    renderHook(
      () =>
        useStress({
          start_date: "2024-01-01",
          end_date: "2024-01-31",
          limit: 100,
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockGarminApi.getStress).toHaveBeenCalledWith({
        start_date: "2024-01-01",
        end_date: "2024-01-31",
        limit: "100",
      });
    });
  });
});
