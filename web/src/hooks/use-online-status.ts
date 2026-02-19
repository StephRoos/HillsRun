"use client";

import { useSyncExternalStore, useRef, useEffect } from "react";
import { toast } from "sonner";

function subscribe(callback: () => void) {
  window.addEventListener("online", callback);
  window.addEventListener("offline", callback);
  return () => {
    window.removeEventListener("online", callback);
    window.removeEventListener("offline", callback);
  };
}

function getSnapshot() {
  return navigator.onLine;
}

function getServerSnapshot() {
  return true;
}

export function useOnlineStatus() {
  const wasOnlineRef = useRef(true);

  const isOnline = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    if (wasOnlineRef.current && !isOnline) {
      toast.warning("You're offline", {
        description: "Showing cached data",
        duration: 4000,
      });
    } else if (!wasOnlineRef.current && isOnline) {
      toast.success("Back online", { duration: 3000 });
    }
    wasOnlineRef.current = isOnline;
  }, [isOnline]);

  return { isOnline };
}
