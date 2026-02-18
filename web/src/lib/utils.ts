import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h${m.toString().padStart(2, "0")}`;
  return `${m}m${s.toString().padStart(2, "0")}s`;
}

export function formatPace(speedMs: number | null): string {
  if (!speedMs || speedMs <= 0) return "—";
  const paceSecondsPerKm = 1000 / speedMs;
  const minutes = Math.floor(paceSecondsPerKm / 60);
  const secs = Math.floor(paceSecondsPerKm % 60);
  return `${minutes}:${secs.toString().padStart(2, "0")} /km`;
}

export function formatDistance(meters: number | null): string {
  if (!meters) return "—";
  return `${(meters / 1000).toFixed(1)} km`;
}

export function formatElevation(meters: number | null): string {
  if (meters == null) return "—";
  return `${Math.round(meters)} m`;
}

export function formatDate(isoString: string | null): string {
  if (!isoString) return "—";
  return new Date(isoString).toLocaleDateString("fr-FR", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

const ACTIVITY_TYPE_LABELS: Record<string, string> = {
  running: "Course",
  trail_running: "Trail",
  hiking: "Rando",
  cycling: "Vélo",
  swimming: "Natation",
  strength_training: "Muscu",
  yoga: "Yoga",
  walking: "Marche",
  multi_sport: "Multi-sport",
};

export function activityTypeLabel(type: string | null): string {
  if (!type) return "Activité";
  return ACTIVITY_TYPE_LABELS[type.toLowerCase()] ?? type.replace(/_/g, " ");
}
