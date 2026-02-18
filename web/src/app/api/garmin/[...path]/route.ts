import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { getGarminUserId } from "@/lib/garmin-user";

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

async function resolveGarminUserId(
  request: NextRequest
): Promise<{ userId: number | null; error?: NextResponse }> {
  try {
    const session = await auth.api.getSession({
      headers: await headers(),
    });
    if (!session?.user?.id) {
      return { userId: null, error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) };
    }

    const garminUserId = await getGarminUserId(session.user.id);
    if (!garminUserId) {
      return { userId: null, error: NextResponse.json({ error: "Garmin account not connected" }, { status: 403 }) };
    }

    return { userId: garminUserId };
  } catch {
    return { userId: null, error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) };
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { userId, error } = await resolveGarminUserId(request);
  if (error) return error;

  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE}${apiPath}${searchParams ? `?${searchParams}` : ""}`;

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

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { userId, error } = await resolveGarminUserId(request);
  if (error) return error;

  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const url = `${API_BASE}${apiPath}`;

  const body = await request.text();

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY ?? "",
      "X-Garmin-User-Id": String(userId),
      "Content-Type": "application/json",
    },
    body: body || "{}",
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
