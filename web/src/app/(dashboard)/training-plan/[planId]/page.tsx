"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2, Play, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useTrainingPlan,
  useTrainingPlanWeek,
  useDeleteTrainingPlan,
  useUpdateTrainingPlanStatus,
} from "@/hooks/use-training-plans";
import type { PlanSession, PlanWeekSummary } from "@/types/garmin";

const PHASE_COLORS: Record<string, string> = {
  base: "bg-blue-500/20 text-blue-400",
  development: "bg-yellow-500/20 text-yellow-400",
  specific: "bg-orange-500/20 text-orange-400",
  taper: "bg-green-500/20 text-green-400",
};

const SESSION_TYPE_COLORS: Record<string, string> = {
  EF: "bg-green-500/20 text-green-400",
  SL: "bg-blue-500/20 text-blue-400",
  TMP: "bg-yellow-500/20 text-yellow-400",
  INT: "bg-red-500/20 text-red-400",
  COT: "bg-orange-500/20 text-orange-400",
  DESC: "bg-purple-500/20 text-purple-400",
  REC: "bg-teal-500/20 text-teal-400",
  RMU: "bg-pink-500/20 text-pink-400",
  REST: "bg-muted text-muted-foreground",
};

const DAY_NAMES = ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;
}

function formatDistance(meters: number | null): string {
  if (!meters) return "—";
  return `${(meters / 1000).toFixed(1)} km`;
}

function WeekView({ planId, week }: { planId: number; week: PlanWeekSummary }) {
  const { data: weekDetail } = useTrainingPlanWeek(planId, week.week_number);
  const sessions = weekDetail?.sessions ?? [];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <Badge className={PHASE_COLORS[week.phase]}>{week.phase}</Badge>
        {week.is_recovery_week && <Badge variant="outline">Recovery</Badge>}
        {week.target_tss && (
          <span className="text-sm text-muted-foreground">TSS: {Math.round(week.target_tss)}</span>
        )}
        {week.target_sessions && (
          <span className="text-sm text-muted-foreground">{week.target_sessions} sessions</span>
        )}
      </div>

      {sessions.length === 0 && (
        <div className="text-sm text-muted-foreground py-4 text-center">Loading sessions...</div>
      )}

      <div className="grid gap-2">
        {sessions.map((session: PlanSession) => (
          <Card key={session.id}>
            <CardContent className="flex items-center gap-4 py-3">
              <div className="w-10 text-center">
                <div className="text-xs text-muted-foreground">{DAY_NAMES[session.day_of_week]}</div>
              </div>
              <Badge className={SESSION_TYPE_COLORS[session.session_type] || "bg-muted"}>
                {session.session_type}
              </Badge>
              <div className="flex-1">
                <p className="font-medium text-sm">{session.title}</p>
                {session.description && (
                  <p className="text-xs text-muted-foreground line-clamp-1">{session.description}</p>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span>{formatDuration(session.target_duration_seconds)}</span>
                {session.target_distance_meters && (
                  <span>{formatDistance(session.target_distance_meters)}</span>
                )}
                {session.hr_zone_primary && (
                  <Badge variant="outline" className="text-xs">
                    Z{session.hr_zone_primary}
                  </Badge>
                )}
                {session.target_tss && (
                  <span className="text-xs">TSS {Math.round(session.target_tss)}</span>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function TrainingPlanDetailPage() {
  const params = useParams();
  const router = useRouter();
  const planId = Number(params.planId);
  const { data: plan, isPending } = useTrainingPlan(planId);
  const deletePlan = useDeleteTrainingPlan();
  const updateStatus = useUpdateTrainingPlanStatus();
  const [activeWeek, setActiveWeek] = useState("1");

  if (isPending) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!plan) {
    return <div className="text-center py-12 text-muted-foreground">Plan not found</div>;
  }

  const weeks = plan.weeks ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/training-plan")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{plan.name}</h1>
            <p className="text-muted-foreground">
              {plan.total_weeks} weeks · {plan.experience_level} · {plan.start_date} to {plan.end_date}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {plan.status === "draft" && (
            <Button
              size="sm"
              onClick={() => updateStatus.mutate({ planId, status: "active" })}
            >
              <Play className="mr-2 h-4 w-4" /> Activate
            </Button>
          )}
          {plan.status === "active" && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => updateStatus.mutate({ planId, status: "completed" })}
            >
              <Square className="mr-2 h-4 w-4" /> Complete
            </Button>
          )}
          <Button
            size="sm"
            variant="destructive"
            onClick={() => {
              deletePlan.mutate(planId);
              router.push("/training-plan");
            }}
          >
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </Button>
        </div>
      </div>

      {weeks.length > 0 && (
        <Tabs value={activeWeek} onValueChange={setActiveWeek}>
          <TabsList className="flex-wrap h-auto gap-1">
            {weeks.map((week: PlanWeekSummary) => (
              <TabsTrigger
                key={week.week_number}
                value={String(week.week_number)}
                className="text-xs"
              >
                W{week.week_number}
                {week.is_recovery_week && " ↓"}
              </TabsTrigger>
            ))}
          </TabsList>
          {weeks.map((week: PlanWeekSummary) => (
            <TabsContent key={week.week_number} value={String(week.week_number)}>
              <WeekView planId={planId} week={week} />
            </TabsContent>
          ))}
        </Tabs>
      )}
    </div>
  );
}
