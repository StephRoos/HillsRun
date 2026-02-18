"use client";

import { useState } from "react";
import { List, CalendarDays, Link } from "lucide-react";
import { WeeklySummary } from "@/components/dashboard/weekly-summary";
import { ReadinessCard } from "@/components/dashboard/readiness-card";
import { TodayActivities } from "@/components/dashboard/today-activities";
import { ActivityList } from "@/components/activity/activity-list";
import { ActivityCalendar } from "@/components/dashboard/activity-calendar";
import { SyncButton } from "@/components/dashboard/sync-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useGarminAccount } from "@/hooks/use-garmin-account";
import NextLink from "next/link";

export default function DashboardPage() {
  const [view, setView] = useState<"list" | "calendar">("list");
  const { data: garminAccount, isLoading } = useGarminAccount();

  if (!isLoading && garminAccount && !garminAccount.connected) {
    return (
      <div className="p-6 space-y-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-center space-y-4">
            <Link className="h-12 w-12 text-muted-foreground" />
            <h2 className="text-lg font-semibold">Connect your Garmin account</h2>
            <p className="text-sm text-muted-foreground max-w-md">
              Link your Garmin Connect account to start syncing your activities, health metrics, and training data.
            </p>
            <Button asChild>
              <NextLink href="/settings">Go to Settings</NextLink>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

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
