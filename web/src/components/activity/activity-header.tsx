"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ActivityDetail } from "@/types/garmin";
import { formatDate, activityTypeLabel } from "@/lib/utils";

export function ActivityHeader({ activity }: { activity: ActivityDetail }) {
  const router = useRouter();

  return (
    <div className="space-y-2">
      <Button
        variant="ghost"
        size="sm"
        className="gap-1 text-muted-foreground"
        onClick={() => router.push("/dashboard")}
      >
        <ArrowLeft className="h-4 w-4" />
        Dashboard
      </Button>
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold">
          {activity.activity_name ?? "Activity"}
        </h1>
        <Badge variant="secondary">
          {activityTypeLabel(activity.activity_type)}
        </Badge>
      </div>
      <p className="text-sm text-muted-foreground">
        {formatDate(activity.start_timestamp)}
      </p>
    </div>
  );
}
