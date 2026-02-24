import { NextResponse } from "next/server";

const VERSION = "1.0.0";
const API_BASE = process.env.GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

export async function GET(): Promise<NextResponse> {
  const timestamp = new Date().toISOString();

  let backendReachable: boolean | undefined = undefined;

  if (API_BASE && API_KEY) {
    try {
      const res = await fetch(`${API_BASE}/health`, {
        headers: { "X-API-Key": API_KEY },
        // Short timeout so we don't block the response
        signal: AbortSignal.timeout(3000),
      });
      backendReachable = res.ok;
    } catch {
      backendReachable = false;
    }
  }

  const body: Record<string, unknown> = {
    status: "ok",
    version: VERSION,
    timestamp,
  };

  if (backendReachable !== undefined) {
    body.backend_reachable = backendReachable;
  }

  return NextResponse.json(body);
}
