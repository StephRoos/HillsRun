import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { invalidateGarminUserCache } from "@/lib/garmin-user";

const API_BASE = process.env.GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

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
    res = await fetch(`${API_BASE}/api/v1/auth/connect/mfa`, {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY ?? "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...body,
        better_auth_user_id: session.user.id,
      }),
    });
  } catch (e) {
    console.error("Failed to reach Garmin API (MFA):", e);
    return NextResponse.json({ error: "Failed to reach Garmin API" }, { status: 502 });
  }

  const text = await res.text();
  let data: Record<string, unknown>;
  try {
    data = JSON.parse(text);
  } catch {
    return NextResponse.json({ error: `Garmin API error (${res.status})` }, { status: 502 });
  }

  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  invalidateGarminUserCache(session.user.id);
  return NextResponse.json(data);
}
