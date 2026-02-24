import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSyncStatus, useTriggerSync } from "../use-sync";
import * as garminApiModule from "@/lib/garmin-api";

vi.mock("@/lib/garmin-api");
vi.mock("sonner", () => ({
  toast: {
    info: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const mockGarminApi = vi.mocked(garminApiModule.garminApi);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  }
  return Wrapper;
}

describe("useSyncStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches sync status", async () => {
    const mockStatus = { running: false, last_sync: "2024-01-01T10:00:00Z" };

    mockGarminApi.getSyncStatus.mockResolvedValueOnce(mockStatus);

    const { result } = renderHook(() => useSyncStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockStatus);
  });

  it("caches status data", async () => {
    const mockStatus = { running: false };

    mockGarminApi.getSyncStatus.mockResolvedValueOnce(mockStatus);

    const { result } = renderHook(() => useSyncStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.getSyncStatus).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(mockStatus);
  });
});

describe("useTriggerSync", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns initial state", () => {
    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isSyncing).toBe(false);
    expect(typeof result.current.trigger).toBe("function");
    expect(typeof result.current.cancel).toBe("function");
  });

  it("triggers sync with API call", async () => {
    mockGarminApi.triggerSync.mockResolvedValueOnce({ job_id: "job-123" });

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.trigger();
    });

    expect(result.current.isSyncing).toBe(true);
    expect(mockGarminApi.triggerSync).toHaveBeenCalled();
  });

  it("handles sync already in progress (409)", async () => {
    mockGarminApi.triggerSync.mockResolvedValueOnce({});

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.trigger();
    });

    expect(result.current.isSyncing).toBe(false);
  });

  it("sets isSyncing to false initially", () => {
    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isSyncing).toBe(false);
  });

  it("prevents concurrent sync triggers", async () => {
    mockGarminApi.triggerSync.mockResolvedValueOnce({ job_id: "job-123" });

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.trigger();
    });

    expect(result.current.isSyncing).toBe(true);

    act(() => {
      result.current.trigger();
    });

    expect(mockGarminApi.triggerSync).toHaveBeenCalledTimes(1);
  });

  it("passes sync options to API", async () => {
    mockGarminApi.triggerSync.mockResolvedValueOnce({ job_id: "job-123" });

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.trigger({ mode: "full", days_back: 30 });
    });

    expect(mockGarminApi.triggerSync).toHaveBeenCalledWith({
      mode: "full",
      days_back: 30,
    });
  });

  it("has cancel function", () => {
    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.cancel).toBe("function");
    act(() => {
      result.current.cancel();
    });
  });

  it("handles trigger error", async () => {
    mockGarminApi.triggerSync.mockRejectedValueOnce(
      new Error("API error")
    );

    const { result } = renderHook(() => useTriggerSync(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.trigger();
    });

    await waitFor(() => {
      expect(result.current.isSyncing).toBe(false);
    });

    expect(mockGarminApi.triggerSync).toHaveBeenCalled();
  });
});
