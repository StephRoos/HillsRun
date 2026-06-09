"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  useAthleteProfile,
  useUpdateAthleteProfile,
  useRaceTargets,
  useCreateRaceTarget,
  useGenerateTrainingPlan,
  useFitnessSnapshot,
} from "@/hooks/use-training-plans";
import { DayPreferencePicker } from "@/components/training-plan/day-preference-picker";
import type { AthleteProfileCreate, DayPreferences, RaceTarget, RaceTargetCreate } from "@/types/garmin";

const STEPS = ["Profile", "Race", "Preferences", "Generate"];

// Running sessions per week by experience level (mirrors _get_session_count in week_builder.py)
const SESSION_COUNT: Record<string, number> = {
  beginner: 3,
  intermediate: 4,
  advanced: 5,
  expert: 6,
};

const DAY_LABELS: Record<number, string> = {
  1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun",
};

/** Parse a "h:mm:ss" or "h:mm" goal time into seconds; null if malformed. */
function parseHmsToSeconds(value: string): number | null {
  const m = value.trim().match(/^(\d{1,2}):([0-5]?\d)(?::([0-5]?\d))?$/);
  if (!m) return null;
  return Number(m[1]) * 3600 + Number(m[2]) * 60 + Number(m[3] ?? 0);
}

/** Format a duration in seconds back to "h:mm:ss" for display. */
function formatSecondsToHms(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function NewTrainingPlanPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  const { data: profile } = useAthleteProfile();
  const updateProfile = useUpdateAthleteProfile();
  const [profileForm, setProfileForm] = useState<AthleteProfileCreate>({
    experience_level: "intermediate",
    available_days_per_week: 4,
    has_hill_access: true,
    has_gym_access: false,
  });

  const { data: races } = useRaceTargets();
  const createRace = useCreateRaceTarget();
  const [raceForm, setRaceForm] = useState<RaceTargetCreate>({
    race_name: "",
    race_date: "",
    distance_km: 0,
    elevation_gain_m: 0,
    objective: "finish",
    discipline: "trail",
  });
  // Goal finish time as "h:mm:ss" (road only); parsed to seconds on submit.
  const [targetTime, setTargetTime] = useState("");
  // Full canonical race (created or existing) — drives the review summary.
  const [selectedRace, setSelectedRace] = useState<RaceTarget | null>(null);
  const selectedRaceId = selectedRace?.id ?? null;

  const [planName, setPlanName] = useState("");
  const [totalWeeks, setTotalWeeks] = useState<number | undefined>();
  const [dayPrefsOverride, setDayPrefsOverride] = useState<DayPreferences>({});
  const [useDayOverride, setUseDayOverride] = useState(false);
  const generatePlan = useGenerateTrainingPlan();
  const { data: fitness } = useFitnessSnapshot();

  if (profile && !profileForm.fc_max && profile.fc_max) {
    setProfileForm({
      experience_level: profile.experience_level || "intermediate",
      available_days_per_week: profile.available_days_per_week || 4,
      has_hill_access: profile.has_hill_access ?? true,
      has_gym_access: profile.has_gym_access ?? false,
      fc_max: profile.fc_max ?? undefined,
      fc_repos: profile.fc_repos ?? undefined,
      birth_date: profile.birth_date ?? undefined,
      height_cm: profile.height_cm ?? undefined,
      gender: profile.gender ?? undefined,
      day_preferences: profile.day_preferences ?? undefined,
    });
  }

  async function handleSaveProfile() {
    await updateProfile.mutateAsync(profileForm);
    setStep(1);
  }

  // Road + a non-empty but unparseable goal time → block submit with feedback.
  const targetTimeInvalid =
    raceForm.discipline === "road" &&
    targetTime.trim() !== "" &&
    parseHmsToSeconds(targetTime) === null;

  async function handleCreateRace() {
    // Road marathons drive the VMA-based engine; attach the goal time (seconds).
    const body: RaceTargetCreate =
      raceForm.discipline === "road"
        ? { ...raceForm, target_time_seconds: parseHmsToSeconds(targetTime) }
        : raceForm;
    const result = await createRace.mutateAsync(body);
    setSelectedRace(result);
    setStep(2);
  }

  function handleSelectExistingRace(race: RaceTarget) {
    setSelectedRace(race);
    setStep(2);
  }

  async function handleGenerate() {
    if (!selectedRaceId) return;
    // Send override preferences if enabled, otherwise backend uses profile defaults
    const overridePrefs = useDayOverride && Object.keys(dayPrefsOverride).length > 0
      ? dayPrefsOverride
      : undefined;
    const result = await generatePlan.mutateAsync({
      race_target_id: selectedRaceId,
      plan_name: planName || undefined,
      total_weeks: totalWeeks,
      day_preferences: overridePrefs,
    });
    const planId = (result as Record<string, unknown>).plan_id;
    router.push(`/training-plan/${planId}`);
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => step > 0 ? setStep(step - 1) : router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">New Training Plan</h1>
          <p className="text-muted-foreground">Step {step + 1} of {STEPS.length}: {STEPS[step]}</p>
        </div>
      </div>

      <div className="flex gap-1">
        {STEPS.map((_, i) => (
          <div key={i} className={`h-1 flex-1 rounded-full ${i <= step ? "bg-primary" : "bg-muted"}`} />
        ))}
      </div>

      {step === 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Athlete Profile</CardTitle>
            <CardDescription>Set up your athlete information for plan calibration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Experience Level</Label>
                <Select value={profileForm.experience_level} onValueChange={(v) => setProfileForm({ ...profileForm, experience_level: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="beginner">Beginner</SelectItem>
                    <SelectItem value="intermediate">Intermediate</SelectItem>
                    <SelectItem value="advanced">Advanced</SelectItem>
                    <SelectItem value="expert">Expert</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Days per Week</Label>
                <Select value={String(profileForm.available_days_per_week)} onValueChange={(v) => setProfileForm({ ...profileForm, available_days_per_week: Number(v) })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2, 3, 4, 5, 6, 7].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n} days
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Max HR (bpm)</Label>
                <Input
                  type="number"
                  value={profileForm.fc_max ?? ""}
                  onChange={(e) =>
                    setProfileForm({
                      ...profileForm,
                      fc_max: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  placeholder="e.g. 185"
                />
              </div>
              <div className="space-y-2">
                <Label>Resting HR (bpm)</Label>
                <Input
                  type="number"
                  value={profileForm.fc_repos ?? ""}
                  onChange={(e) =>
                    setProfileForm({
                      ...profileForm,
                      fc_repos: e.target.value ? Number(e.target.value) : undefined,
                    })
                  }
                  placeholder="e.g. 55"
                />
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Switch
                  checked={profileForm.has_hill_access}
                  onCheckedChange={(v) =>
                    setProfileForm({ ...profileForm, has_hill_access: v })
                  }
                />
                <Label>Hill access</Label>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={profileForm.has_gym_access}
                  onCheckedChange={(v) =>
                    setProfileForm({ ...profileForm, has_gym_access: v })
                  }
                />
                <Label>Gym access</Label>
              </div>
            </div>
            <div className="space-y-2">
              <Label>Preferred Training Days</Label>
              <p className="text-xs text-muted-foreground">
                Optional: choose which days you prefer for each session type
              </p>
              <DayPreferencePicker
                value={profileForm.day_preferences ?? {}}
                onChange={(prefs) =>
                  setProfileForm({ ...profileForm, day_preferences: prefs })
                }
                maxRunningSessions={SESSION_COUNT[profileForm.experience_level ?? ""] ?? 4}
              />
            </div>
            <Button
              onClick={handleSaveProfile}
              disabled={updateProfile.isPending}
              className="w-full"
            >
              {updateProfile.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ArrowRight className="mr-2 h-4 w-4" />
              )}
              Save & Continue
            </Button>
          </CardContent>
        </Card>
      )}

      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Target Race</CardTitle>
            <CardDescription>Define your target race or select an existing one</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {races && races.length > 0 && (
              <div className="space-y-2">
                <Label>Existing Races</Label>
                {races.map((race) => (
                  <div
                    key={race.id}
                    className="flex items-center justify-between p-3 rounded-md border cursor-pointer hover:bg-accent/30"
                    onClick={() => handleSelectExistingRace(race)}
                  >
                    <div>
                      <p className="font-medium">{race.race_name}</p>
                      <p className="text-sm text-muted-foreground">
                        {race.distance_km}km ·{" "}
                        {race.discipline === "road"
                          ? `Road${race.target_time_seconds ? ` · ${formatSecondsToHms(race.target_time_seconds)}` : ""}`
                          : `${race.elevation_gain_m}m D+`}{" "}
                        · {race.race_date}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                ))}
                <div className="relative py-2">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-card px-2 text-muted-foreground">or create new</span>
                  </div>
                </div>
              </div>
            )}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Race Name</Label>
                <Input
                  value={raceForm.race_name}
                  onChange={(e) => setRaceForm({ ...raceForm, race_name: e.target.value })}
                  placeholder="e.g. Trail des Aiguilles Rouges"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Race Date</Label>
                  <Input
                    type="date"
                    value={raceForm.race_date}
                    onChange={(e) => setRaceForm({ ...raceForm, race_date: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Distance (km)</Label>
                  <Input
                    type="number"
                    value={raceForm.distance_km || ""}
                    onChange={(e) =>
                      setRaceForm({ ...raceForm, distance_km: Number(e.target.value) })
                    }
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Discipline</Label>
                  <Select
                    value={raceForm.discipline}
                    onValueChange={(v) => setRaceForm({ ...raceForm, discipline: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="trail">Trail</SelectItem>
                      <SelectItem value="road">Road (marathon)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Objective</Label>
                  <Select value={raceForm.objective} onValueChange={(v) => setRaceForm({ ...raceForm, objective: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="finish">Finish</SelectItem>
                      <SelectItem value="midpack">Midpack</SelectItem>
                      <SelectItem value="performance">Performance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                {raceForm.discipline === "road" ? (
                  <div className="space-y-2">
                    <Label>Target time (h:mm:ss)</Label>
                    <Input
                      value={targetTime}
                      onChange={(e) => setTargetTime(e.target.value)}
                      placeholder="3:30:00"
                      aria-invalid={targetTimeInvalid}
                    />
                    {targetTimeInvalid ? (
                      <p className="text-xs text-destructive">
                        Use the format h:mm:ss (e.g. 3:30:00).
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Drives marathon paces (VMA-based). Leave empty to skip.
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Label>Elevation Gain (m)</Label>
                    <Input
                      type="number"
                      value={raceForm.elevation_gain_m || ""}
                      onChange={(e) =>
                        setRaceForm({ ...raceForm, elevation_gain_m: Number(e.target.value) })
                      }
                    />
                  </div>
                )}
              </div>
              <Button
                onClick={handleCreateRace}
                disabled={createRace.isPending || !raceForm.race_name || !raceForm.race_date || !raceForm.distance_km || targetTimeInvalid}
                className="w-full"
              >
                {createRace.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ArrowRight className="mr-2 h-4 w-4" />
                )}
                Create Race & Continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Plan Preferences</CardTitle>
            <CardDescription>Configure your training plan options</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Plan Name (optional)</Label>
              <Input
                value={planName}
                onChange={(e) => setPlanName(e.target.value)}
                placeholder="Auto-generated if empty"
              />
            </div>
            <div className="space-y-2">
              <Label>Total Weeks (optional, auto-calculated from race date)</Label>
              <Input
                type="number"
                min={6}
                max={30}
                value={totalWeeks ?? ""}
                onChange={(e) =>
                  setTotalWeeks(e.target.value ? Number(e.target.value) : undefined)
                }
                placeholder="6-30 weeks"
              />
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Switch
                  checked={useDayOverride}
                  onCheckedChange={setUseDayOverride}
                />
                <Label>Override day preferences for this plan</Label>
              </div>
              {useDayOverride && (
                <DayPreferencePicker
                  value={dayPrefsOverride}
                  onChange={setDayPrefsOverride}
                  maxRunningSessions={SESSION_COUNT[profileForm.experience_level ?? ""] ?? 4}
                />
              )}
            </div>
            {fitness && (
              <div className="rounded-md border p-4 space-y-2">
                <h4 className="font-medium text-sm">Current Fitness Snapshot</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {fitness.vo2_max && (
                    <div>
                      VO2max: <span className="font-medium">{fitness.vo2_max}</span>
                    </div>
                  )}
                  {fitness.resting_hr && (
                    <div>
                      Resting HR: <span className="font-medium">{fitness.resting_hr} bpm</span>
                    </div>
                  )}
                  {fitness.weekly_volume_km && (
                    <div>
                      Weekly Volume:{" "}
                      <span className="font-medium">{Math.round(fitness.weekly_volume_km)} km</span>
                    </div>
                  )}
                  {fitness.recent_long_run_km && (
                    <div>
                      Recent Long Run:{" "}
                      <span className="font-medium">{Math.round(fitness.recent_long_run_km)} km</span>
                    </div>
                  )}
                  {fitness.weight_kg && (
                    <div>
                      Weight: <span className="font-medium">{fitness.weight_kg} kg</span>
                    </div>
                  )}
                  {fitness.avg_training_readiness && (
                    <div>
                      Readiness:{" "}
                      <span className="font-medium">
                        {Math.round(fitness.avg_training_readiness)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
            <Button onClick={() => setStep(3)} className="w-full">
              <ArrowRight className="mr-2 h-4 w-4" />
              Review & Generate
            </Button>
          </CardContent>
        </Card>
      )}

      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Generate Plan</CardTitle>
            <CardDescription>Review your settings and generate the training plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-md border p-4 space-y-1 text-sm">
              <div>
                Experience: <span className="font-medium">{profileForm.experience_level}</span>
              </div>
              <div>
                Days/week: <span className="font-medium">{profileForm.available_days_per_week}</span>
              </div>
              {planName && (
                <div>
                  Plan name: <span className="font-medium">{planName}</span>
                </div>
              )}
              {totalWeeks && (
                <div>
                  Duration: <span className="font-medium">{totalWeeks} weeks</span>
                </div>
              )}
              {selectedRace && (
                <>
                  <div>
                    Race: <span className="font-medium">{selectedRace.race_name}</span>
                  </div>
                  <div>
                    Discipline:{" "}
                    <span className="font-medium capitalize">{selectedRace.discipline}</span> ·{" "}
                    {selectedRace.distance_km}km
                  </div>
                  <div>
                    Objective:{" "}
                    <span className="font-medium capitalize">{selectedRace.objective}</span>
                  </div>
                  {selectedRace.discipline === "road" ? (
                    <div>
                      Target time:{" "}
                      <span className="font-medium">
                        {selectedRace.target_time_seconds
                          ? formatSecondsToHms(selectedRace.target_time_seconds)
                          : "—"}
                      </span>
                    </div>
                  ) : (
                    <div>
                      Elevation: <span className="font-medium">{selectedRace.elevation_gain_m}m D+</span>
                    </div>
                  )}
                </>
              )}
              {(() => {
                const prefs = useDayOverride ? dayPrefsOverride : profileForm.day_preferences;
                if (!prefs || (!prefs.long_run && !prefs.quality?.length && !prefs.strength && !prefs.easy_run?.length)) return null;
                return (
                  <div className="pt-1 border-t space-y-0.5">
                    <div className="font-medium text-xs text-muted-foreground">Day Preferences{useDayOverride ? " (override)" : ""}</div>
                    {prefs.long_run && <div>Long Run: <span className="font-medium">{DAY_LABELS[prefs.long_run]}</span></div>}
                    {prefs.quality && prefs.quality.length > 0 && (
                      <div>Quality: <span className="font-medium">{prefs.quality.map((d) => DAY_LABELS[d]).join(", ")}</span></div>
                    )}
                    {prefs.easy_run && prefs.easy_run.length > 0 && (
                      <div>Easy Run: <span className="font-medium">{prefs.easy_run.map((d) => DAY_LABELS[d]).join(", ")}</span></div>
                    )}
                    {prefs.strength && prefs.strength.length > 0 && (
                      <div>Strength: <span className="font-medium">{prefs.strength.map((d) => DAY_LABELS[d]).join(", ")}</span></div>
                    )}
                  </div>
                );
              })()}
            </div>
            <Button
              onClick={handleGenerate}
              disabled={generatePlan.isPending || !selectedRaceId}
              className="w-full"
              size="lg"
            >
              {generatePlan.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating plan...
                </>
              ) : (
                "Generate Training Plan"
              )}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
