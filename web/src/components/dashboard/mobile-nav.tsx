"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Calendar, TrendingUp, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { OfflineIndicator } from "@/components/dashboard/offline-indicator";
import { useCoachContext } from "@/lib/coach-context";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Calendar", href: "/calendar", icon: Calendar },
  { label: "Trends", href: "/trends", icon: TrendingUp },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();
  const { isViewingAthlete, athleteName } = useCoachContext();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-card md:hidden">
      {isViewingAthlete && (
        <div className="bg-primary/10 text-primary text-xs text-center py-1 font-medium">
          Viewing {athleteName}&apos;s data
        </div>
      )}
      <div className="absolute -top-8 left-1/2 -translate-x-1/2">
        <OfflineIndicator />
      </div>
      <div className="flex items-center justify-around py-2">
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
