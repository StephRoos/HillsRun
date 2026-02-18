/**
 * Resolve garmin user_id from Better-Auth session user ID.
 * Calls FastAPI /api/v1/auth/status and caches the result for 5 minutes.
 */

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
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

export async function getGarminUserStatus(
  betterAuthUserId: string
): Promise<GarminUserStatus> {
  const cached = cache.get(betterAuthUserId);
  if (cached && cached.expires > Date.now()) {
    return cached.data;
  }

  const url = `${API_BASE}/api/v1/auth/status?better_auth_user_id=${encodeURIComponent(betterAuthUserId)}`;
  const res = await fetch(url, {
    headers: { "X-API-Key": API_KEY ?? "" },
  });

  if (!res.ok) {
    throw new Error(`Failed to get Garmin user status: ${res.status}`);
  }

  const data: GarminUserStatus = await res.json();
  cache.set(betterAuthUserId, { data, expires: Date.now() + TTL_MS });
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
