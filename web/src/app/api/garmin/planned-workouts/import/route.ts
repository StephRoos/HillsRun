import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { getGarminUserId } from "@/lib/garmin-user";

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

export async function POST(request: NextRequest) {
  try {
    const session = await auth.api.getSession({
      headers: await headers(),
    });
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const garminUserId = await getGarminUserId(session.user.id);
    if (!garminUserId) {
      return NextResponse.json({ error: "Garmin account not connected" }, { status: 403 });
    }

    const formData = await request.formData();
    const url = `${API_BASE}/api/v1/planned-workouts/import`;

    const res = await fetch(url, {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY ?? "",
        "X-Garmin-User-Id": String(garminUserId),
      },
      body: formData,
    });

    if (!res.ok) {
      return NextResponse.json(
        { error: `Garmin API error: ${res.status}` },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
}
