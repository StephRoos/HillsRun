import { NextRequest, NextResponse } from "next/server";

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
  return NextResponse.json(data);
}
