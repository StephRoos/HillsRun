import { describe, it, expect, vi, beforeEach } from "vitest";

const mockFetch = vi.fn();
global.fetch = mockFetch;

// Set environment variables before importing the module
process.env.GARMIN_API_URL = "https://api.garmin.local";
process.env.GARMIN_API_KEY = "test-key-123";

// Now import after env vars are set
import {
  getGarminUserStatus,
  getGarminUserId,
  invalidateGarminUserCache,
} from "../garmin-user";

describe("getGarminUserStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    invalidateGarminUserCache("user-1");
    invalidateGarminUserCache("user-2");
  });

  it("fetches user status from API", async () => {
    const mockStatus = {
      connected: true,
      garmin_display_name: "John Doe",
      user_id: 123,
      last_sync: "2024-01-01T10:00:00Z",
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    });

    const result = await getGarminUserStatus("user-1");

    expect(result).toEqual(mockStatus);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/auth/status?better_auth_user_id=user-1"),
      expect.objectContaining({
        headers: expect.any(Object),
      })
    );
  });

  it("caches successful connected responses", async () => {
    const mockStatus = {
      connected: true,
      garmin_display_name: "John Doe",
      user_id: 123,
      last_sync: "2024-01-01T10:00:00Z",
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockStatus,
    });

    // First call
    await getGarminUserStatus("user-1");

    // Second call should use cache
    const result = await getGarminUserStatus("user-1");

    expect(result).toEqual(mockStatus);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("does not cache unsuccessful responses", async () => {
    const mockStatus = {
      connected: false,
      garmin_display_name: null,
      user_id: null,
      last_sync: null,
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    });

    // First call
    await getGarminUserStatus("user-1");

    // Second call should fetch again
    await getGarminUserStatus("user-1");

    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("deduplicates concurrent requests for same user", async () => {
    const mockStatus = {
      connected: true,
      garmin_display_name: "John Doe",
      user_id: 123,
      last_sync: "2024-01-01T10:00:00Z",
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    });

    // Make 3 concurrent requests
    const results = await Promise.all([
      getGarminUserStatus("user-1"),
      getGarminUserStatus("user-1"),
      getGarminUserStatus("user-1"),
    ]);

    expect(results).toEqual([mockStatus, mockStatus, mockStatus]);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("does not deduplicate requests for different users", async () => {
    const mockStatus1 = {
      connected: true,
      garmin_display_name: "John",
      user_id: 1,
      last_sync: "2024-01-01T10:00:00Z",
    };

    const mockStatus2 = {
      connected: true,
      garmin_display_name: "Jane",
      user_id: 2,
      last_sync: "2024-01-01T10:00:00Z",
    };

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus1,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockStatus2,
      });

    const results = await Promise.all([
      getGarminUserStatus("user-1"),
      getGarminUserStatus("user-2"),
    ]);

    expect(results).toEqual([mockStatus1, mockStatus2]);
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("throws error on API failure", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    await expect(getGarminUserStatus("user-1")).rejects.toThrow(
      /Failed to get Garmin user status/
    );
  });

  it("URL-encodes the better_auth_user_id parameter", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connected: false,
        garmin_display_name: null,
        user_id: null,
        last_sync: null,
      }),
    });

    await getGarminUserStatus("user@example.com");

    const url = mockFetch.mock.calls[0][0];
    expect(url).toContain("user%40example.com");
  });
});

describe("getGarminUserId", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    invalidateGarminUserCache("user-1");
  });

  it("returns user_id when connected", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connected: true,
        garmin_display_name: "John",
        user_id: 123,
        last_sync: "2024-01-01T10:00:00Z",
      }),
    });

    const result = await getGarminUserId("user-1");
    expect(result).toBe(123);
  });

  it("returns null when not connected", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connected: false,
        garmin_display_name: null,
        user_id: null,
        last_sync: null,
      }),
    });

    const result = await getGarminUserId("user-1");
    expect(result).toBeNull();
  });

  it("uses cached result from getGarminUserStatus", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        connected: true,
        garmin_display_name: "John",
        user_id: 123,
        last_sync: "2024-01-01T10:00:00Z",
      }),
    });

    // Call getGarminUserStatus first
    await getGarminUserStatus("user-1");

    // Call getGarminUserId, should use cache
    const result = await getGarminUserId("user-1");

    expect(result).toBe(123);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});

describe("invalidateGarminUserCache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    invalidateGarminUserCache("user-1");
    invalidateGarminUserCache("user-2");
  });

  it("removes cached entry for user", async () => {
    const mockStatus = {
      connected: true,
      garmin_display_name: "John",
      user_id: 123,
      last_sync: "2024-01-01T10:00:00Z",
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    });

    // First call
    await getGarminUserStatus("user-1");
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Invalidate cache
    invalidateGarminUserCache("user-1");

    // Second call should fetch again
    await getGarminUserStatus("user-1");
    expect(mockFetch).toHaveBeenCalledTimes(2);
  });

  it("does not affect other cached users", async () => {
    const mockStatus = {
      connected: true,
      garmin_display_name: "John",
      user_id: 123,
      last_sync: "2024-01-01T10:00:00Z",
    };

    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => mockStatus,
    });

    // Cache both users
    await getGarminUserStatus("user-1");
    await getGarminUserStatus("user-2");

    // Invalidate user-1 only
    invalidateGarminUserCache("user-1");

    // User-1 should fetch again
    await getGarminUserStatus("user-1");
    expect(mockFetch).toHaveBeenCalledTimes(3);

    // User-2 should still use cache
    await getGarminUserStatus("user-2");
    expect(mockFetch).toHaveBeenCalledTimes(3);
  });
});
