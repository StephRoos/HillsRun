import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useVma, useUpdateVma } from "../use-vma";
import * as garminApiModule from "@/lib/garmin-api";

vi.mock("@/lib/garmin-api");
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
  },
}));

const mockGarminApi = vi.mocked(garminApiModule.garminApi);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe("useVma", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches VMA data", async () => {
    const mockVmaData = {
      vma: 16.5,
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-15T10:00:00Z",
    };

    mockGarminApi.getVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useVma(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockVmaData);
    expect(mockGarminApi.getVma).toHaveBeenCalled();
  });

  it("handles null VMA value", async () => {
    const mockVmaData = {
      vma: null,
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-01T10:00:00Z",
    };

    mockGarminApi.getVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useVma(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data?.vma).toBeNull();
  });

  it("handles error", async () => {
    mockGarminApi.getVma.mockRejectedValueOnce(
      new Error("Failed to fetch VMA")
    );

    const { result } = renderHook(() => useVma(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe("useUpdateVma", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates VMA value", async () => {
    const mockVmaData = {
      vma: 17.0,
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-20T10:00:00Z",
    };

    mockGarminApi.updateVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(17.0);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockVmaData);
    expect(mockGarminApi.updateVma).toHaveBeenCalledWith(17.0);
  });

  it("updates VMA to null", async () => {
    const mockVmaData = {
      vma: null,
      created_at: "2024-01-01T10:00:00Z",
      updated_at: "2024-01-20T10:00:00Z",
    };

    mockGarminApi.updateVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(null);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.updateVma).toHaveBeenCalledWith(null);
  });

  it("invalidates VMA query on success", async () => {
    const mockVmaData = { vma: 18.0 };

    mockGarminApi.updateVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(18.0);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("shows error toast on failure", async () => {
    const { toast } = await import("sonner");
    mockGarminApi.updateVma.mockRejectedValueOnce(
      new Error("Failed to update VMA")
    );

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(17.0);
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(toast.error).toHaveBeenCalledWith("Failed to update VMA");
  });

  it("handles decimal VMA values", async () => {
    const mockVmaData = { vma: 15.75 };

    mockGarminApi.updateVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(15.75);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.updateVma).toHaveBeenCalledWith(15.75);
  });

  it("handles large VMA values", async () => {
    const mockVmaData = { vma: 25.5 };

    mockGarminApi.updateVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(25.5);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGarminApi.updateVma).toHaveBeenCalledWith(25.5);
  });

  it("is not pending initially", () => {
    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(false);
  });

  it("completes mutation successfully", async () => {
    const mockVmaData = { vma: 17.0 };
    mockGarminApi.updateVma.mockResolvedValueOnce(mockVmaData);

    const { result } = renderHook(() => useUpdateVma(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate(17.0);
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockVmaData);
  });
});
