import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { Prisma } from "@/generated/prisma/client";

const API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
const API_KEY = process.env.GARMIN_API_KEY;

// GET still proxies to FastAPI
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const url = `${API_BASE}/api/v1/activities/${id}`;

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

  // Enrich with custom_name from DB (in case FastAPI doesn't have it yet)
  try {
    const rows = await prisma.$queryRaw<{ custom_name: string | null }[]>`
      SELECT custom_name FROM activities WHERE activity_id = ${BigInt(id)}
    `;
    if (rows.length > 0) {
      data.custom_name = rows[0].custom_name;
    }
  } catch {
    // Column might not exist yet, ignore
  }

  return NextResponse.json(data);
}

// PATCH updates custom_name directly in DB
export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const body = await request.json();
  const customName: string | null = body.custom_name ?? null;

  try {
    // Ensure column exists (idempotent)
    await prisma.$executeRaw`
      ALTER TABLE activities ADD COLUMN IF NOT EXISTS custom_name VARCHAR(255)
    `;

    // Update
    const activityId = BigInt(id);
    const updated = await prisma.$executeRaw`
      UPDATE activities SET custom_name = ${customName} WHERE activity_id = ${activityId}
    `;

    if (updated === 0) {
      return NextResponse.json(
        { error: "Activity not found" },
        { status: 404 }
      );
    }

    // Return updated activity
    const rows = await prisma.$queryRaw<Record<string, unknown>[]>`
      SELECT activity_id, activity_name, custom_name, activity_type, sport_type,
             start_timestamp, duration_seconds, distance_meters,
             average_speed, max_speed, calories, average_hr, max_hr,
             elevation_gain_meters, elevation_loss_meters,
             training_stress_score, vo2_max_value, device_name, num_laps,
             aerobic_training_effect, anaerobic_training_effect,
             average_pace, max_pace, average_running_cadence, max_running_cadence,
             average_bike_cadence, max_bike_cadence, average_power, max_power,
             normalized_power, intensity_factor, min_elevation_meters, max_elevation_meters,
             average_temperature, max_temperature, min_temperature,
             training_effect, avg_vertical_oscillation, avg_ground_contact_time,
             avg_stride_length, lactate_threshold_bpm, description,
             manual_activity, pr, favorite
      FROM activities WHERE activity_id = ${activityId}
    `;

    if (rows.length === 0) {
      return NextResponse.json(
        { error: "Activity not found" },
        { status: 404 }
      );
    }

    // Serialize bigint to number for JSON
    const row = rows[0];
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(row)) {
      result[key] = typeof value === "bigint" ? Number(value) : value;
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error("Failed to update activity custom_name:", error);
    return NextResponse.json(
      { error: "Failed to update activity" },
      { status: 500 }
    );
  }
}
