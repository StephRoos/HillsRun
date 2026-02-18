"use client";

import { WeeklySummary } from "@/components/dashboard/weekly-summary";
import { ReadinessCard } from "@/components/dashboard/readiness-card";
import { ActivityList } from "@/components/activity/activity-list";

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      <WeeklySummary />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityList />
        </div>
        <div>
          <ReadinessCard />
        </div>
      </div>
    </div>
  );
}
