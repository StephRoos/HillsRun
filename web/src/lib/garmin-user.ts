/**
 * Resolve garmin user_id from Better-Auth session user ID.
 * Calls FastAPI /api/v1/auth/status and caches the result for 5 minutes.
 * Uses request deduplication to prevent thundering herd on page load.
 */

const API_BASE = process.env.GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

interface GarminUserStatus {
  connected: boolean;
  garmin_display_name: string | null;
  user_id: number | null;
  last_sync: string | null;
}

interface CacheEntry {
  data: GarminUserStatus;
  expires: number;
}

const TTL_MS = 5 * 60 * 1000; // 5 minutes
const cache = new Map<string, CacheEntry>();
const pending = new Map<string, Promise<GarminUserStatus>>();

export async function getGarminUserStatus(
  betterAuthUserId: string
): Promise<GarminUserStatus> {
  const cached = cache.get(betterAuthUserId);
  if (cached && cached.expires > Date.now()) {
    return cached.data;
  }

  // Deduplicate concurrent requests for the same user
  const inflight = pending.get(betterAuthUserId);
  if (inflight) return inflight;

  const promise = fetchGarminUserStatus(betterAuthUserId);
  pending.set(betterAuthUserId, promise);
  try {
    return await promise;
  } finally {
    pending.delete(betterAuthUserId);
  }
}

async function fetchGarminUserStatus(
  betterAuthUserId: string
): Promise<GarminUserStatus> {
  const url = `${API_BASE}/api/v1/auth/status?better_auth_user_id=${encodeURIComponent(betterAuthUserId)}`;
  const res = await fetch(url, {
    headers: { "X-API-Key": API_KEY ?? "" },
  });

  if (!res.ok) {
    throw new Error(`Failed to get Garmin user status: ${res.status}`);
  }

  const data: GarminUserStatus = await res.json();
  // Only cache positive results — don't cache "not connected" because
  // Vercel serverless instances don't share memory, so invalidation
  // after connect won't reach other instances.
  if (data.connected) {
    cache.set(betterAuthUserId, { data, expires: Date.now() + TTL_MS });
  }
  return data;
}

export async function getGarminUserId(
  betterAuthUserId: string
): Promise<number | null> {
  const status = await getGarminUserStatus(betterAuthUserId);
  return status.connected ? status.user_id : null;
}

export function invalidateGarminUserCache(betterAuthUserId: string) {
  cache.delete(betterAuthUserId);
}
