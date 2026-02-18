"use client";

import { WeeklySummary } from "@/components/dashboard/weekly-summary";
import { ReadinessCard } from "@/components/dashboard/readiness-card";
import { TodayActivities } from "@/components/dashboard/today-activities";
import { ActivityList } from "@/components/activity/activity-list";
import { SyncButton } from "@/components/dashboard/sync-button";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <SyncButton />
      </div>
      <WeeklySummary />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityList />
        </div>
        <div className="space-y-6">
          <TodayActivities />
          <ReadinessCard />
        </div>
      </div>
    </div>
  );
}
