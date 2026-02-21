import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { invalidateGarminUserCache } from "@/lib/garmin-user";

const API_BASE = process.env.GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

// Garmin SSO login can take 15-30s — increase Vercel function timeout
export const maxDuration = 60;

export async function POST(request: NextRequest) {
  const session = await auth.api.getSession({
    headers: await headers(),
  });
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();

  let res: Response;
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 55_000);

    res = await fetch(`${API_BASE}/api/v1/auth/connect`, {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY ?? "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...body,
        better_auth_user_id: session.user.id,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeout);
  } catch (e) {
    const message = e instanceof Error && e.name === "AbortError"
      ? "Garmin login timed out — please try again"
      : "Failed to reach Garmin API";
    console.error("Garmin connect error:", e);
    return NextResponse.json({ error: message }, { status: 502 });
  }

  const text = await res.text();
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(text);
  } catch {
    console.error("Garmin API returned non-JSON:", res.status, text.slice(0, 200));
    return NextResponse.json({ error: `Garmin API error (${res.status})` }, { status: 502 });
  }

  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  // Invalidate cache so next request picks up the new connection
  invalidateGarminUserCache(session.user.id);

  return NextResponse.json(data);
}
