import { prisma } from "./prisma";

export interface GarminActivity {
  activity_id: bigint;
  activity_name: string | null;
  activity_type: string | null;
  sport_type: string | null;
  start_timestamp: Date | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  elevation_gain_meters: number | null;
  elevation_loss_meters: number | null;
  average_hr: number | null;
  max_hr: number | null;
  average_pace: number | null;
  calories: number | null;
}

export async function getRecentActivities(limit = 20, userId?: number) {
  if (userId != null) {
    return prisma.$queryRaw<GarminActivity[]>`
      SELECT activity_id, activity_name, activity_type, sport_type,
             start_timestamp, duration_seconds, distance_meters,
             elevation_gain_meters, elevation_loss_meters,
             average_hr, max_hr, average_pace, calories
      FROM activities
      WHERE user_id = ${userId}
      ORDER BY start_timestamp DESC
      LIMIT ${limit}
    `;
  }
  return prisma.$queryRaw<GarminActivity[]>`
    SELECT activity_id, activity_name, activity_type, sport_type,
           start_timestamp, duration_seconds, distance_meters,
           elevation_gain_meters, elevation_loss_meters,
           average_hr, max_hr, average_pace, calories
    FROM activities
    ORDER BY start_timestamp DESC
    LIMIT ${limit}
  `;
}

export async function getTrailActivities(limit = 20, userId?: number) {
  if (userId != null) {
    return prisma.$queryRaw<GarminActivity[]>`
      SELECT activity_id, activity_name, activity_type, sport_type,
             start_timestamp, duration_seconds, distance_meters,
             elevation_gain_meters, elevation_loss_meters,
             average_hr, max_hr, average_pace, calories
      FROM activities
      WHERE user_id = ${userId} AND sport_type IN ('trail_running', 'running')
      ORDER BY start_timestamp DESC
      LIMIT ${limit}
    `;
  }
  return prisma.$queryRaw<GarminActivity[]>`
    SELECT activity_id, activity_name, activity_type, sport_type,
           start_timestamp, duration_seconds, distance_meters,
           elevation_gain_meters, elevation_loss_meters,
           average_hr, max_hr, average_pace, calories
    FROM activities
    WHERE sport_type IN ('trail_running', 'running')
    ORDER BY start_timestamp DESC
    LIMIT ${limit}
  `;
}

export interface TrainingReadiness {
  calendar_date: Date;
  score: number | null;
  score_feedback: string | null;
  hrv_status: string | null;
  sleep_score: number | null;
  acute_load: number | null;
  chronic_load: number | null;
}

export async function getLatestTrainingReadiness(userId?: number) {
  let results: TrainingReadiness[];
  if (userId != null) {
    results = await prisma.$queryRaw<TrainingReadiness[]>`
      SELECT calendar_date, score, score_feedback, hrv_status,
             sleep_score, acute_load, chronic_load
      FROM training_readiness
      WHERE user_id = ${userId}
      ORDER BY calendar_date DESC
      LIMIT 1
    `;
  } else {
    results = await prisma.$queryRaw<TrainingReadiness[]>`
      SELECT calendar_date, score, score_feedback, hrv_status,
             sleep_score, acute_load, chronic_load
      FROM training_readiness
      ORDER BY calendar_date DESC
      LIMIT 1
    `;
  }
  return results[0] ?? null;
}

export interface DailySummary {
  calendar_date: Date;
  total_steps: number | null;
  total_distance_meters: number | null;
  active_calories: number | null;
  resting_heart_rate: number | null;
  average_stress_level: number | null;
}

export async function getRecentDailySummaries(days = 7, userId?: number) {
  if (userId != null) {
    return prisma.$queryRaw<DailySummary[]>`
      SELECT calendar_date, total_steps, total_distance_meters,
             active_calories, resting_heart_rate, average_stress_level
      FROM daily_summary
      WHERE user_id = ${userId}
      ORDER BY calendar_date DESC
      LIMIT ${days}
    `;
  }
  return prisma.$queryRaw<DailySummary[]>`
    SELECT calendar_date, total_steps, total_distance_meters,
           active_calories, resting_heart_rate, average_stress_level
    FROM daily_summary
    ORDER BY calendar_date DESC
    LIMIT ${days}
  `;
}
