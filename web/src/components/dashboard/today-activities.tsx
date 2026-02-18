"use client";

import { useMemo } from "react";
import { Activity as ActivityIcon } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useActivities } from "@/hooks/use-activities";

export function TodayActivities() {
  const today = new Date().toISOString().slice(0, 10);
  const { data } = useActivities({ limit: 50 });

  const todayActivities = useMemo(() => {
    if (!data?.data) return [];
    return data.data.filter(
      (a) => a.start_timestamp && a.start_timestamp.slice(0, 10) === today
    );
  }, [data, today]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">
          Today&apos;s activities
        </CardTitle>
        <ActivityIcon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {todayActivities.length === 0 ? (
          <p className="text-sm text-muted-foreground">No activities yet</p>
        ) : (
          <div className="space-y-2">
            {todayActivities.map((a) => (
              <div key={a.activity_id} className="flex items-center justify-between text-sm">
                <span className="font-medium">{a.activity_name ?? a.activity_type}</span>
                <span className="text-muted-foreground">
                  {a.distance_meters ? `${(a.distance_meters / 1000).toFixed(1)} km` : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
