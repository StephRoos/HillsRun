/**
 * Server-side coach access verification with in-memory cache.
 */

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

interface CacheEntry {
  hasAccess: boolean;
  expires: number;
}

const TTL_MS = 5 * 60 * 1000; // 5 minutes
const cache = new Map<string, CacheEntry>();

export async function verifyCoachAccess(
  coachBetterAuthId: string,
  athleteUserId: number
): Promise<boolean> {
  const key = `${coachBetterAuthId}:${athleteUserId}`;
  const cached = cache.get(key);
  if (cached && cached.expires > Date.now()) {
    return cached.hasAccess;
  }

  const url = `${API_BASE}/api/v1/coaching/check-access?athlete_user_id=${athleteUserId}`;
  const res = await fetch(url, {
    headers: {
      "X-API-Key": API_KEY ?? "",
      "X-Better-Auth-User-Id": coachBetterAuthId,
    },
  });

  if (!res.ok) {
    cache.set(key, { hasAccess: false, expires: Date.now() + TTL_MS });
    return false;
  }

  const data: { has_access: boolean } = await res.json();
  cache.set(key, { hasAccess: data.has_access, expires: Date.now() + TTL_MS });
  return data.has_access;
}
