import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { getGarminUserId } from "@/lib/garmin-user";
import { verifyCoachAccess } from "@/lib/coach-access";

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

async function resolveRequest(
  request: NextRequest
): Promise<{
  garminUserId: number | null;
  betterAuthUserId: string | null;
  coachBetterAuthId: string | null;
  error?: NextResponse;
}> {
  try {
    const session = await auth.api.getSession({
      headers: await headers(),
    });
    if (!session?.user?.id) {
      return { garminUserId: null, betterAuthUserId: null, coachBetterAuthId: null, error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) };
    }

    const betterAuthUserId = session.user.id;
    const viewAsAthlete = request.headers.get("X-View-As-Athlete");

    if (viewAsAthlete) {
      const athleteId = parseInt(viewAsAthlete, 10);
      if (isNaN(athleteId)) {
        return { garminUserId: null, betterAuthUserId, coachBetterAuthId: null, error: NextResponse.json({ error: "Invalid athlete ID" }, { status: 400 }) };
      }
      const hasAccess = await verifyCoachAccess(betterAuthUserId, athleteId);
      if (!hasAccess) {
        return { garminUserId: null, betterAuthUserId, coachBetterAuthId: null, error: NextResponse.json({ error: "Not authorized to view this athlete" }, { status: 403 }) };
      }
      return { garminUserId: athleteId, betterAuthUserId, coachBetterAuthId: betterAuthUserId };
    }

    const garminUserId = await getGarminUserId(betterAuthUserId);
    if (!garminUserId) {
      return { garminUserId: null, betterAuthUserId, coachBetterAuthId: null, error: NextResponse.json({ error: "Garmin account not connected" }, { status: 403 }) };
    }

    return { garminUserId, betterAuthUserId, coachBetterAuthId: null };
  } catch {
    return { garminUserId: null, betterAuthUserId: null, coachBetterAuthId: null, error: NextResponse.json({ error: "Unauthorized" }, { status: 401 }) };
  }
}

function buildHeaders(garminUserId: number, betterAuthUserId: string | null, coachBetterAuthId: string | null): Record<string, string> {
  const h: Record<string, string> = {
    "X-API-Key": API_KEY ?? "",
    "X-Garmin-User-Id": String(garminUserId),
  };
  if (betterAuthUserId) h["X-Better-Auth-User-Id"] = betterAuthUserId;
  if (coachBetterAuthId) h["X-Coach-Better-Auth-Id"] = coachBetterAuthId;
  return h;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { garminUserId, betterAuthUserId, coachBetterAuthId, error } = await resolveRequest(request);
  if (error) return error;

  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE}${apiPath}${searchParams ? `?${searchParams}` : ""}`;

  const res = await fetch(url, {
    headers: buildHeaders(garminUserId!, betterAuthUserId, coachBetterAuthId),
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
  const { garminUserId, betterAuthUserId, coachBetterAuthId, error } = await resolveRequest(request);
  if (error) return error;

  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const url = `${API_BASE}${apiPath}`;

  const body = await request.text();

  const res = await fetch(url, {
    method: "POST",
    headers: {
      ...buildHeaders(garminUserId!, betterAuthUserId, coachBetterAuthId),
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

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { garminUserId, betterAuthUserId, coachBetterAuthId, error } = await resolveRequest(request);
  if (error) return error;

  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const url = `${API_BASE}${apiPath}`;

  const body = await request.text();

  const res = await fetch(url, {
    method: "PATCH",
    headers: {
      ...buildHeaders(garminUserId!, betterAuthUserId, coachBetterAuthId),
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

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { garminUserId, betterAuthUserId, coachBetterAuthId, error } = await resolveRequest(request);
  if (error) return error;

  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const url = `${API_BASE}${apiPath}`;

  const res = await fetch(url, {
    method: "DELETE",
    headers: buildHeaders(garminUserId!, betterAuthUserId, coachBetterAuthId),
  });

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  if (!res.ok) {
    return NextResponse.json(
      { error: `Garmin API error: ${res.status}` },
      { status: res.status }
    );
  }

  const data = await res.json();
  return NextResponse.json(data);
}
