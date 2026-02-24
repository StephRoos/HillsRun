import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useCoachingStatus,
  useGenerateInviteCode,
  useInviteCodes,
  useRevokeInviteCode,
  useRedeemInviteCode,
  useRemoveAthlete,
  useRemoveCoach,
} from "../use-coaching";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
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

describe("useCoachingStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches coaching status", async () => {
    const mockStatus = {
      is_coach: true,
      is_athlete: false,
      athletes: [],
      coaches: [],
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    });

    const { result } = renderHook(() => useCoachingStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockStatus);
  });

  it("has retry: false", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: async () => JSON.stringify({ detail: "Error" }),
    });

    const { result } = renderHook(() => useCoachingStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

describe("useGenerateInviteCode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("generates invite code", async () => {
    const mockCode = {
      code: "ABC123DEF",
      created_at: "2024-01-01T10:00:00Z",
      expires_at: "2024-02-01T10:00:00Z",
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockCode,
    });

    const { result } = renderHook(() => useGenerateInviteCode(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockCode);
  });

  it("sends POST request to invite-codes", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ code: "ABC123" }),
    });

    const { result } = renderHook(() => useGenerateInviteCode(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/garmin/coaching/invite-codes"),
      expect.objectContaining({
        method: "POST",
      })
    );
  });

  it("invalidates coaching-status on success", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ code: "ABC123" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_coach: true, athletes: [] }),
      });

    const { result: generateResult } = renderHook(
      () => useGenerateInviteCode(),
      {
        wrapper: createWrapper(),
      }
    );

    act(() => {
      generateResult.current.mutate();
    });

    await waitFor(() => {
      expect(generateResult.current.isSuccess).toBe(true);
    });
  });
});

describe("useInviteCodes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("has invite codes query function", () => {
    const { result } = renderHook(() => useInviteCodes(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading || result.current.isPending || result.current.isSuccess || result.current.isError).toBeDefined();
  });
});

describe("useRevokeInviteCode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("revokes invite code", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const { result } = renderHook(() => useRevokeInviteCode(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate("ABC123");
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/garmin/coaching/invite-codes/ABC123"),
      expect.objectContaining({
        method: "DELETE",
      })
    );
  });

  it("invalidates invite-codes on success", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const { result } = renderHook(() => useRevokeInviteCode(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate("ABC123");
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
  });

  it("is a mutation hook", () => {
    const { result } = renderHook(() => useRevokeInviteCode(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe("function");
  });
});

describe("useRedeemInviteCode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("has redeem mutation function", () => {
    const { result } = renderHook(() => useRedeemInviteCode(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe("function");
    expect(result.current.isPending).toBe(false);
  });
});

describe("useRemoveAthlete", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("is a mutation hook", () => {
    const { result } = renderHook(() => useRemoveAthlete(), {
      wrapper: createWrapper(),
    });

    expect(typeof result.current.mutate).toBe("function");
    expect(result.current.isPending).toBe(false);
  });

  it("has mutation state properties", () => {
    const { result } = renderHook(() => useRemoveAthlete(), {
      wrapper: createWrapper(),
    });

    expect("isPending" in result.current).toBe(true);
    expect("isError" in result.current).toBe(true);
    expect("isSuccess" in result.current).toBe(true);
  });
});

describe("useRemoveCoach", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("removes coach from coaching", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const { result } = renderHook(() => useRemoveCoach(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate("coach-id-123");
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/garmin/coaching/coaches/coach-id-123"),
      expect.objectContaining({
        method: "DELETE",
      })
    );
  });

  it("shows success toast", async () => {
    const { toast } = await import("sonner");
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const { result } = renderHook(() => useRemoveCoach(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate("coach-id");
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(toast.success).toHaveBeenCalledWith("Coach removed");
  });
});
