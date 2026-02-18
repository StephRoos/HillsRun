"use client";

import { useState } from "react";
import { List, CalendarDays } from "lucide-react";
import { WeeklySummary } from "@/components/dashboard/weekly-summary";
import { ReadinessCard } from "@/components/dashboard/readiness-card";
import { TodayActivities } from "@/components/dashboard/today-activities";
import { ActivityList } from "@/components/activity/activity-list";
import { ActivityCalendar } from "@/components/dashboard/activity-calendar";
import { SyncButton } from "@/components/dashboard/sync-button";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const [view, setView] = useState<"list" | "calendar">("list");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center gap-2">
          <div className="flex border border-border rounded-md">
            <Button
              variant={view === "list" ? "default" : "ghost"}
              size="icon"
              className="h-8 w-8 rounded-r-none"
              onClick={() => setView("list")}
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={view === "calendar" ? "default" : "ghost"}
              size="icon"
              className="h-8 w-8 rounded-l-none"
              onClick={() => setView("calendar")}
            >
              <CalendarDays className="h-4 w-4" />
            </Button>
          </div>
          <SyncButton />
        </div>
      </div>
      <WeeklySummary />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          {view === "list" ? <ActivityList /> : <ActivityCalendar />}
        </div>
        <div className="space-y-6">
          <TodayActivities />
          <ReadinessCard />
        </div>
      </div>
    </div>
  );
}
