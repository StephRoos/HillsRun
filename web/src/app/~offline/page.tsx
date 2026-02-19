"use client";

import { WifiOff } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function OfflinePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4 p-6">
      <WifiOff className="h-16 w-16 text-muted-foreground" />
      <h1 className="text-4xl font-bold">Offline</h1>
      <p className="text-muted-foreground text-center">
        No network connection. Your cached data is still available.
      </p>
      <Button onClick={() => window.location.reload()}>Try again</Button>
    </div>
  );
}
