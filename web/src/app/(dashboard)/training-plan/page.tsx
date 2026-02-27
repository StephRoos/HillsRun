"use client";

import { useRouter } from "next/navigation";
import { Plus, Target, Calendar, Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTrainingPlans, useUpdateTrainingPlanStatus } from "@/hooks/use-training-plans";
import type { TrainingPlanSummary } from "@/types/garmin";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  active: "bg-green-500/20 text-green-400",
  completed: "bg-blue-500/20 text-blue-400",
  cancelled: "bg-red-500/20 text-red-400",
};

function formatDate(dateStr: string): string {
  return new Date(dateStr + "T00:00:00").toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function TrainingPlanPage() {
  const router = useRouter();
  const { data, isPending } = useTrainingPlans();
  const updateStatus = useUpdateTrainingPlanStatus();

  const plans = data?.data ?? [];
  const activePlan = plans.find((p: TrainingPlanSummary) => p.status === "active");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Training Plan</h1>
          <p className="text-muted-foreground">Generate and manage your trail training plans</p>
        </div>
        <Button onClick={() => router.push("/training-plan/new")}>
          <Plus className="mr-2 h-4 w-4" />
          New Plan
        </Button>
      </div>

      {isPending && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      )}

      {!isPending && plans.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Target className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No training plans yet</h3>
            <p className="text-muted-foreground mb-4 text-center max-w-md">
              Create your first training plan by setting up your athlete profile and a target race.
            </p>
            <Button onClick={() => router.push("/training-plan/new")}>
              <Plus className="mr-2 h-4 w-4" />
              Create Training Plan
            </Button>
          </CardContent>
        </Card>
      )}

      {activePlan && (
        <Card className="border-primary/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-primary" />
                  {activePlan.name}
                </CardTitle>
                <CardDescription>
                  {formatDate(activePlan.start_date)} — {formatDate(activePlan.end_date)} · {activePlan.total_weeks} weeks · {activePlan.experience_level}
                </CardDescription>
              </div>
              <Badge className={STATUS_COLORS[activePlan.status]}>{activePlan.status}</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <Button variant="outline" onClick={() => router.push(`/training-plan/${activePlan.id}`)}>
              View Plan Details
            </Button>
          </CardContent>
        </Card>
      )}

      {plans.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">All Plans</h2>
          {plans.map((plan: TrainingPlanSummary) => (
            <Card key={plan.id} className="cursor-pointer hover:bg-accent/30 transition-colors" onClick={() => router.push(`/training-plan/${plan.id}`)}>
              <CardContent className="flex items-center justify-between py-4">
                <div className="flex items-center gap-4">
                  <Calendar className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{plan.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatDate(plan.start_date)} — {formatDate(plan.end_date)} · {plan.total_weeks} weeks
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={STATUS_COLORS[plan.status]}>{plan.status}</Badge>
                  {plan.status === "draft" && (
                    <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); updateStatus.mutate({ planId: plan.id, status: "active" }); }}>
                      Activate
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
