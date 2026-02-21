import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { getGarminUserId } from "@/lib/garmin-user";

const API_BASE = process.env.GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

async function resolveGarminUserId(): Promise<{
  userId: number | null;
  error?: NextResponse;
}> {
  try {
    const session = await auth.api.getSession({
      headers: await headers(),
    });
    if (!session?.user?.id) {
      return {
        userId: null,
        error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }),
      };
    }

    const garminUserId = await getGarminUserId(session.user.id);
    if (!garminUserId) {
      return {
        userId: null,
        error: NextResponse.json(
          { error: "Garmin account not connected" },
          { status: 403 }
        ),
      };
    }

    return { userId: garminUserId };
  } catch {
    return {
      userId: null,
      error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }),
    };
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await resolveGarminUserId();
  if (error) return error;

  const { id } = await params;
  const url = `${API_BASE}/api/v1/activities/${id}`;

  const res = await fetch(url, {
    headers: {
      "X-API-Key": API_KEY ?? "",
      "X-Garmin-User-Id": String(userId),
    },
  });

  if (!res.ok) {
    return NextResponse.json(
      { error: `Garmin API error: ${res.status}` },
      { status: res.status }
    );
  }

  const data = await res.json();
  return NextResponse.json(data);
}

// PATCH proxies to FastAPI (activities table is on NAS, not Neon)
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { userId, error } = await resolveGarminUserId();
  if (error) return error;

  const { id } = await params;
  const body = await request.text();

  const res = await fetch(`${API_BASE}/api/v1/activities/${id}`, {
    method: "PATCH",
    headers: {
      "X-API-Key": API_KEY ?? "",
      "X-Garmin-User-Id": String(userId),
      "Content-Type": "application/json",
    },
    body,
  });

  if (!res.ok) {
    return NextResponse.json(
      { error: `Garmin API error: ${res.status}` },
      { status: res.status }
    );
  }

  const data = await res.json();
  return NextResponse.json(data);
}
