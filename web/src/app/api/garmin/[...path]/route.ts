import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE}${apiPath}${searchParams ? `?${searchParams}` : ""}`;

  const res = await fetch(url, {
    headers: { "X-API-Key": API_KEY ?? "" },
  });

  if (!res.ok) {
    return NextResponse.json(
      { error: `Garmin API error: ${res.status}` },
      { status: res.status }
    );
  }

  const data = await res.json();

  // Enrich activity listings with custom_name from DB
  if (path.join("/") === "activities" && data.data && Array.isArray(data.data)) {
    try {
      const ids = data.data.map((a: { activity_id: number }) => BigInt(a.activity_id));
      if (ids.length > 0) {
        const rows = await prisma.$queryRaw<{ activity_id: bigint; custom_name: string | null }[]>`
          SELECT activity_id, custom_name FROM activities
          WHERE activity_id = ANY(${ids})
          AND custom_name IS NOT NULL
        `;
        const nameMap = new Map(rows.map(r => [Number(r.activity_id), r.custom_name]));
        for (const activity of data.data) {
          activity.custom_name = nameMap.get(activity.activity_id) ?? null;
        }
      }
    } catch {
      // Column might not exist yet, ignore
    }
  }

  return NextResponse.json(data);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const apiPath = `/api/v1/${path.join("/")}`;
  const url = `${API_BASE}${apiPath}`;

  const body = await request.text();

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY ?? "",
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
