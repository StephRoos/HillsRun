"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LayoutDashboard, Calendar, TrendingUp, Settings, LogOut, Mountain, Users } from "lucide-react";
import { signOut, useSession } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { OfflineIndicator } from "@/components/dashboard/offline-indicator";
import { useCoachingStatus } from "@/hooks/use-coaching";
import { useCoachContext } from "@/lib/coach-context";
import { setViewAsAthlete } from "@/lib/garmin-api";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Calendar", href: "/calendar", icon: Calendar },
  { label: "Trends", href: "/trends", icon: TrendingUp },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: session } = useSession();
  const { data: coachingStatus } = useCoachingStatus();
  const { athleteUserId, setAthlete } = useCoachContext();

  const athletes = coachingStatus?.athletes ?? [];

  function handleAthleteChange(value: string) {
    if (value === "self") {
      setAthlete(null, null);
      setViewAsAthlete(null);
    } else {
      const athlete = athletes.find((a) => String(a.athlete_user_id) === value);
      if (athlete) {
        setAthlete(athlete.athlete_user_id, athlete.display_name || athlete.email || `User #${athlete.athlete_user_id}`);
        setViewAsAthlete(athlete.athlete_user_id);
      }
    }
  }

  return (
    <aside className="hidden md:flex md:w-64 md:flex-col md:border-r md:border-border bg-card">
      <div className="flex h-14 items-center gap-2 px-4">
        <Mountain className="h-5 w-5 text-primary" />
        <span className="text-lg font-bold">HillsRun</span>
      </div>

      <Separator />

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}

        {athletes.length > 0 && (
          <>
            <Separator className="my-2" />
            <div className="px-3 py-1">
              <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
                <Users className="h-3.5 w-3.5" />
                Viewing as
              </div>
              <Select
                value={athleteUserId ? String(athleteUserId) : "self"}
                onValueChange={handleAthleteChange}
              >
                <SelectTrigger className="h-8 text-xs">
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
          </>
        )}
      </nav>

      <div className="px-3 pb-1">
        <OfflineIndicator />
      </div>

      <Separator />

      <div className="p-3 space-y-2">
        {session?.user && (
          <p className="px-3 text-xs text-muted-foreground truncate">
            {session.user.name || session.user.email}
          </p>
        )}
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-3 text-muted-foreground"
          onClick={async () => {
            await signOut();
            router.push("/login");
          }}
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </aside>
  );
}
