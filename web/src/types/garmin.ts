// Pagination wrapper from FastAPI
export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface Page<T> {
  data: T[];
  pagination: Pagination;
}

// Activities
export interface Activity {
  activity_id: number;
  activity_name: string | null;
  custom_name: string | null;
  activity_type: string | null;
  sport_type: string | null;
  start_timestamp: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  average_speed: number | null;
  max_speed: number | null;
  calories: number | null;
  average_hr: number | null;
  max_hr: number | null;
  elevation_gain_meters: number | null;
  elevation_loss_meters: number | null;
  training_stress_score: number | null;
  vo2_max_value: number | null;
  device_name: string | null;
  num_laps: number | null;
  aerobic_training_effect: number | null;
  anaerobic_training_effect: number | null;
}

export interface ActivityDetail extends Activity {
  average_pace: number | null;
  max_pace: number | null;
  average_running_cadence: number | null;
  max_running_cadence: number | null;
  average_bike_cadence: number | null;
  max_bike_cadence: number | null;
  average_power: number | null;
  max_power: number | null;
  normalized_power: number | null;
  intensity_factor: number | null;
  min_elevation_meters: number | null;
  max_elevation_meters: number | null;
  average_temperature: number | null;
  max_temperature: number | null;
  min_temperature: number | null;
  training_effect: number | null;
  avg_vertical_oscillation: number | null;
  avg_ground_contact_time: number | null;
  avg_stride_length: number | null;
  lactate_threshold_bpm: number | null;
  description: string | null;
  manual_activity: boolean | null;
  pr: boolean | null;
  favorite: boolean | null;
}

export interface ActivitySplit {
  split_index: number | null;
  split_type: string | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  average_speed: number | null;
  average_hr: number | null;
  calories: number | null;
  elevation_gain: number | null;
}

// Daily health
export interface DailySummary {
  calendar_date: string;
  total_steps: number | null;
  step_goal: number | null;
  total_distance_meters: number | null;
  active_calories: number | null;
  bmr_calories: number | null;
  total_calories: number | null;
  floors_ascended: number | null;
  floors_descended: number | null;
  moderate_intensity_minutes: number | null;
  vigorous_intensity_minutes: number | null;
  resting_heart_rate: number | null;
  average_heart_rate: number | null;
  average_stress_level: number | null;
  max_stress_level: number | null;
}

export interface SleepData {
  calendar_date: string;
  total_sleep_seconds: number | null;
  deep_sleep_seconds: number | null;
  light_sleep_seconds: number | null;
  rem_sleep_seconds: number | null;
  awake_seconds: number | null;
  sleep_score: number | null;
  sleep_quality: string | null;
}

export interface BodyBattery {
  calendar_date: string;
  charged_value: number | null;
  drained_value: number | null;
  highest_value: number | null;
  lowest_value: number | null;
}

export interface StressData {
  calendar_date: string;
  average_stress_level: number | null;
  max_stress_level: number | null;
}

// Advanced metrics
export interface HrvData {
  calendar_date: string;
  weekly_avg: number | null;
  last_night_avg: number | null;
  last_night_5_min_high: number | null;
  hrv_status: string | null;
}

export interface TrainingReadiness {
  calendar_date: string;
  score: number | null;
  score_feedback: string | null;
  hrv_status: string | null;
  sleep_score: number | null;
  recent_training_load: number | null;
  acute_load: number | null;
  chronic_load: number | null;
}

export interface FitnessMetrics {
  calendar_date: string;
  vo2_max: number | null;
  vo2_max_running: number | null;
  vo2_max_cycling: number | null;
  fitness_age: number | null;
  lactate_threshold_bpm: number | null;
  lactate_threshold_speed: number | null;
}

// Body
export interface BodyComposition {
  timestamp: string;
  weight_kg: number | null;
  bmi: number | null;
  body_fat_percentage: number | null;
  muscle_mass_kg: number | null;
}

// Planned workouts
export interface PlannedWorkout {
  id: number;
  user_id: number;
  planned_date: string;
  sport_type: string;
  title: string;
  description: string | null;
  planned_duration_seconds: number | null;
  planned_distance_meters: number | null;
  intensity: string;
  completed: boolean;
  created_by_user_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PlannedWorkoutCreate {
  planned_date: string;
  sport_type: string;
  title: string;
  description?: string;
  planned_duration_seconds?: number;
  planned_distance_meters?: number;
  intensity?: string;
}

export interface PlannedWorkoutUpdate {
  planned_date?: string;
  sport_type?: string;
  title?: string;
  description?: string;
  planned_duration_seconds?: number;
  planned_distance_meters?: number;
  intensity?: string;
  completed?: boolean;
}

export interface BulkImportResult {
  imported: number;
  errors: string[];
}

// VMA
export interface VmaData {
  manual_vma: number | null;
  estimated_vma: number | null;
  vo2_max: number | null;
}

// Coaching
export interface InviteCode {
  id: number;
  code: string;
  coach_better_auth_id: string;
  status: string;
  redeemed_by_user_id: number | null;
  created_at: string | null;
  expires_at: string | null;
  redeemed_at: string | null;
}

export interface CoachAthlete {
  athlete_user_id: number;
  display_name: string | null;
  email: string | null;
  status: string;
  linked_at: string | null;
}

export interface CoachInfo {
  coach_better_auth_id: string;
  coach_name: string | null;
  coach_email: string | null;
  status: string;
  linked_at: string | null;
}

export interface CoachingStatus {
  coaching_enabled: boolean;
  athletes: CoachAthlete[];
  coaches: CoachInfo[];
}

// Day preferences for training session placement
export interface DayPreferences {
  long_run?: number;
  quality?: number[];
  strength?: number[];
  easy_run?: number[];
}

// Training Plans
export interface WorkoutBlock {
  name: string;
  duration_seconds: number;
  hr_zone: number | null;
  description: string;
}

export interface AthleteProfile {
  id: number;
  user_id: number;
  birth_date: string | null;
  gender: string | null;
  height_cm: number | null;
  experience_level: string;
  available_days_per_week: number;
  available_slots: Record<string, string[]> | null;
  injury_history: string | null;
  has_hill_access: boolean;
  has_gym_access: boolean;
  fc_max: number | null;
  fc_repos: number | null;
  fthr: number | null;
  day_preferences: DayPreferences | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface AthleteProfileCreate {
  birth_date?: string;
  gender?: string;
  height_cm?: number;
  experience_level?: string;
  available_days_per_week?: number;
  available_slots?: Record<string, string[]>;
  injury_history?: string;
  has_hill_access?: boolean;
  has_gym_access?: boolean;
  fc_max?: number;
  fc_repos?: number;
  fthr?: number;
  day_preferences?: DayPreferences;
}

export interface RaceTarget {
  id: number;
  user_id: number;
  race_name: string;
  race_date: string;
  distance_km: number;
  elevation_gain_m: number;
  elevation_loss_m: number;
  altitude_min_m: number;
  altitude_max_m: number;
  technical_percent: number;
  cutoff_hours: number | null;
  itra_points: number | null;
  objective: string;
  elevation_profile: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface RaceTargetCreate {
  race_name: string;
  race_date: string;
  distance_km: number;
  elevation_gain_m?: number;
  elevation_loss_m?: number;
  altitude_min_m?: number;
  altitude_max_m?: number;
  technical_percent?: number;
  cutoff_hours?: number;
  itra_points?: number;
  objective?: string;
}

export interface GeneratePlanRequest {
  race_target_id: number;
  plan_name?: string;
  total_weeks?: number;
  start_date?: string;
  day_preferences?: DayPreferences;
}

export interface TrainingPlanSummary {
  id: number;
  user_id: number;
  race_target_id: number;
  name: string;
  status: string;
  start_date: string;
  end_date: string;
  total_weeks: number;
  experience_level: string;
  created_by_user_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PlanWeekSummary {
  id: number;
  plan_id: number;
  week_number: number;
  phase: string;
  is_recovery_week: boolean;
  target_tss: number | null;
  target_volume_km: number | null;
  target_elevation_m: number | null;
  target_sessions: number | null;
  notes: string | null;
}

export interface PlanSession {
  id: number;
  plan_id: number;
  week_id: number;
  planned_workout_id: number | null;
  day_of_week: number;
  session_type: string;
  title: string;
  description: string | null;
  sport_type: string;
  target_duration_seconds: number | null;
  target_distance_meters: number | null;
  target_elevation_gain_m: number | null;
  target_tss: number | null;
  hr_zone_primary: number | null;
  intensity: string;
  blocks: WorkoutBlock[] | null;
  sort_order: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface TrainingPlanDetail extends TrainingPlanSummary {
  weeks: PlanWeekSummary[];
  generation_params: Record<string, unknown> | null;
}

export interface PlanWeekDetail extends PlanWeekSummary {
  sessions: PlanSession[];
}

export interface FitnessSnapshot {
  vo2_max: number | null;
  resting_hr: number | null;
  max_hr: number | null;
  weight_kg: number | null;
  vma_kmh: number | null;
  weekly_volume_km: number | null;
  weekly_elevation_m: number | null;
  avg_training_readiness: number | null;
  chronic_load: number | null;
  acute_load: number | null;
  recent_long_run_km: number | null;
  recent_long_run_duration_s: number | null;
  avg_sleep_score: number | null;
  avg_hrv: number | null;
}
