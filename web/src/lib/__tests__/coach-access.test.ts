import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

let verifyCoachAccess: (
  coachBetterAuthId: string,
  athleteUserId: number
) => Promise<boolean>;

const mockFetch = vi.fn();

beforeEach(async () => {
  vi.clearAllMocks();
  vi.stubGlobal("fetch", mockFetch);
  vi.stubEnv("GARMIN_API_URL", "https://api.test.com");
  vi.stubEnv("GARMIN_API_KEY", "test-key");
  // Re-import module to reset cache
  vi.resetModules();
  const mod = await import("../coach-access");
  verifyCoachAccess = mod.verifyCoachAccess;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("verifyCoachAccess", () => {
  it("returns true when API confirms access", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_access: true }),
    });

    const result = await verifyCoachAccess("coach-123", 456);
    expect(result).toBe(true);
  });

  it("returns false when API denies access", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_access: false }),
    });

    const result = await verifyCoachAccess("coach-123", 456);
    expect(result).toBe(false);
  });

  it("returns false on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
    });

    const result = await verifyCoachAccess("coach-123", 456);
    expect(result).toBe(false);
  });

  it("sends correct headers", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_access: true }),
    });

    await verifyCoachAccess("coach-123", 456);

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: {
          "X-API-Key": "test-key",
          "X-Better-Auth-User-Id": "coach-123",
        },
      })
    );
  });

  it("sends correct URL with athlete_user_id query param", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_access: true }),
    });

    await verifyCoachAccess("coach-123", 456);

    expect(mockFetch).toHaveBeenCalledWith(
      "https://api.test.com/api/v1/coaching/check-access?athlete_user_id=456",
      expect.any(Object)
    );
  });

  it("caches result and does not re-fetch within TTL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_access: true }),
    });

    await verifyCoachAccess("coach-123", 456);
    await verifyCoachAccess("coach-123", 456);

    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("re-fetches after cache expires", async () => {
    vi.useFakeTimers();

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ has_access: true }),
    });

    await verifyCoachAccess("coach-123", 456);
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Advance time past TTL (5 minutes = 300000 ms)
    vi.advanceTimersByTime(5 * 60 * 1000 + 1);

    await verifyCoachAccess("coach-123", 456);
    expect(mockFetch).toHaveBeenCalledTimes(2);

    vi.useRealTimers();
  });

  it("caches negative results too", async () => {
    vi.useFakeTimers();

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ has_access: false }),
    });

    await verifyCoachAccess("coach-123", 456);
    await verifyCoachAccess("coach-123", 456);

    expect(mockFetch).toHaveBeenCalledTimes(1);

    vi.useRealTimers();
  });
});
