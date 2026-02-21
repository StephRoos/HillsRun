import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { invalidateGarminUserCache } from "@/lib/garmin-user";

const API_BASE = process.env.GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

export async function POST() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const res = await fetch(`${API_BASE}/api/v1/auth/disconnect`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY ?? "",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      better_auth_user_id: session.user.id,
    }),
  });

  const data = await res.json();

  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  // Invalidate cache
  invalidateGarminUserCache(session.user.id);

  return NextResponse.json(data);
}
