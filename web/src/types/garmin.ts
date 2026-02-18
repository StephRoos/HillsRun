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
