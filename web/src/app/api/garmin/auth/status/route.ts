import { NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { getGarminUserStatus } from "@/lib/garmin-user";

export async function GET() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const status = await getGarminUserStatus(session.user.id);
    return NextResponse.json(status);
  } catch (error) {
    console.error("Failed to get Garmin status:", error);
    return NextResponse.json(
      { connected: false, garmin_display_name: null, user_id: null, last_sync: null }
    );
  }
}
