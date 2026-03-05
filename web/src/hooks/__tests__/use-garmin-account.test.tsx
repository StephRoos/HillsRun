import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useGarminAccount,
  useConnectGarmin,
  useSubmitMfa,
  useDisconnectGarmin,
} from "../use-garmin-account";

// Mock sonner toast — use vi.hoisted so the variable exists when vi.mock factory runs
const { mockToast } = vi.hoisted(() => ({
  mockToast: { error: vi.fn(), success: vi.fn() },
}));
vi.mock("sonner", () => ({ toast: mockToast }));

// Global fetch mock
const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

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

describe("useGarminAccount", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches account status", async () => {
    const status = {
      connected: true,
      garmin_display_name: "Runner",
      user_id: 42,
      last_sync: "2024-01-01T00:00:00Z",
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(status),
    });

    const { result } = renderHook(() => useGarminAccount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(status);
    expect(mockFetch).toHaveBeenCalledWith("/api/garmin/auth/status");
  });

  it("throws on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

    const { result } = renderHook(() => useGarminAccount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe("Failed to get Garmin account status");
  });
});

describe("useConnectGarmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("connects successfully and shows toast", async () => {
    const connectResult = {
      connected: true,
      garmin_display_name: "Runner",
      user_id: 42,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(connectResult),
    });
    // Sync trigger call
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

    const { result } = renderHook(() => useConnectGarmin(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ email: "test@test.com", password: "pass123" });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith("/api/garmin/auth/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: "test@test.com", password: "pass123" }),
    });
    expect(mockToast.success).toHaveBeenCalledWith(
      "Garmin account connected! Syncing your data..."
    );
  });

  it("handles MFA flow without toast", async () => {
    const connectResult = {
      connected: false,
      needs_mfa: true,
      mfa_session_id: "session-123",
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(connectResult),
    });

    const { result } = renderHook(() => useConnectGarmin(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ email: "test@test.com", password: "pass123" });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // No success toast on MFA redirect
    expect(mockToast.success).not.toHaveBeenCalled();
    expect(result.current.data?.needs_mfa).toBe(true);
    expect(result.current.data?.mfa_session_id).toBe("session-123");
  });

  it("shows error toast on failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: () => Promise.resolve(JSON.stringify({ detail: "Invalid credentials" })),
    });

    const { result } = renderHook(() => useConnectGarmin(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ email: "bad@test.com", password: "wrong" });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Invalid credentials");
  });

  it("parses non-JSON error response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Server error"),
    });

    const { result } = renderHook(() => useConnectGarmin(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({ email: "test@test.com", password: "pass" });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Request failed (500)");
  });
});

describe("useSubmitMfa", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits MFA code and triggers sync", async () => {
    const connectResult = { connected: true, user_id: 42 };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(connectResult),
    });
    // Sync trigger
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) });

    const { result } = renderHook(() => useSubmitMfa(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        mfa_session_id: "session-123",
        mfa_code: "654321",
      });
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith("/api/garmin/auth/connect/mfa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mfa_session_id: "session-123",
        mfa_code: "654321",
      }),
    });
    expect(mockToast.success).toHaveBeenCalled();
  });

  it("shows error on MFA failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve(JSON.stringify({ error: "Invalid MFA code" })),
    });

    const { result } = renderHook(() => useSubmitMfa(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate({
        mfa_session_id: "session-123",
        mfa_code: "000000",
      });
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Invalid MFA code");
  });
});

describe("useDisconnectGarmin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("disconnects and shows toast", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ disconnected: true }),
    });

    const { result } = renderHook(() => useDisconnectGarmin(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockFetch).toHaveBeenCalledWith("/api/garmin/auth/disconnect", {
      method: "POST",
    });
    expect(mockToast.success).toHaveBeenCalledWith("Garmin account disconnected");
  });

  it("shows error toast on disconnect failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const { result } = renderHook(() => useDisconnectGarmin(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(mockToast.error).toHaveBeenCalledWith("Failed to disconnect Garmin account");
  });
});
