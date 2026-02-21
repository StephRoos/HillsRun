"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Calendar, TrendingUp, Settings } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { OfflineIndicator } from "@/components/dashboard/offline-indicator";
import { useCoachContext } from "@/lib/coach-context";
import { useCoachingStatus } from "@/hooks/use-coaching";
import { setViewAsAthlete } from "@/lib/garmin-api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Calendar", href: "/calendar", icon: Calendar },
  { label: "Trends", href: "/trends", icon: TrendingUp },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const { athleteUserId, setAthlete } = useCoachContext();
  const { data: coachingStatus } = useCoachingStatus();

  const athletes = coachingStatus?.athletes ?? [];

  function handleAthleteChange(value: string) {
    if (value === "self") {
      setAthlete(null, null);
      setViewAsAthlete(null);
    } else {
      const athlete = athletes.find((a) => String(a.athlete_user_id) === value);
      if (athlete) {
        setAthlete(
          athlete.athlete_user_id,
          athlete.display_name || athlete.email || `User #${athlete.athlete_user_id}`
        );
        setViewAsAthlete(athlete.athlete_user_id);
      }
    }
    queryClient.invalidateQueries();
  }

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card md:hidden">
      {athletes.length > 0 && (
        <div className="px-3 py-1.5 border-b border-border">
          <Select
            value={athleteUserId ? String(athleteUserId) : "self"}
            onValueChange={handleAthleteChange}
          >
            <SelectTrigger className="h-7 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="self">My data</SelectItem>
              {athletes.map((a) => (
                <SelectItem
                  key={a.athlete_user_id}
                  value={String(a.athlete_user_id)}
                >
                  {a.display_name || a.email || `User #${a.athlete_user_id}`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      <div className="absolute -top-8 left-1/2 -translate-x-1/2">
        <OfflineIndicator />
      </div>
      <div className="flex items-center justify-around py-2" style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}>
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 px-3 py-1 text-xs transition-colors",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground"
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
