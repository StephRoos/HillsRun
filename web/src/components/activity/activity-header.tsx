"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { ArrowLeft, Pencil, Trophy, Star, Watch } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ActivityDetail } from "@/types/garmin";
import { formatDate, activityTypeLabel } from "@/lib/utils";
import { useUpdateActivity } from "@/hooks/use-activities";

export function ActivityHeader({ activity }: { activity: ActivityDetail }) {
  const router = useRouter();
  const displayName = activity.custom_name ?? activity.activity_name ?? "Activity";
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(displayName);
  const inputRef = useRef<HTMLInputElement>(null);
  const savingRef = useRef(false);
  const mutation = useUpdateActivity(String(activity.activity_id));

  useEffect(() => {
    if (editing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [editing]);

  // Sync displayName when activity data changes (after mutation success)
  useEffect(() => {
    if (!editing) {
      setDraft(displayName);
    }
  }, [displayName, editing]);

  function startEditing() {
    setDraft(displayName);
    setEditing(true);
    savingRef.current = false;
  }

  const save = useCallback(() => {
    // Guard against double-fire (Enter + blur)
    if (savingRef.current) return;
    savingRef.current = true;
    setEditing(false);

    const trimmed = draft.trim();
    // If empty or same as original Garmin name, clear custom_name
    const newCustomName =
      !trimmed || trimmed === (activity.activity_name ?? "Activity")
        ? null
        : trimmed;
    // Only mutate if different from current
    if (newCustomName !== (activity.custom_name ?? null)) {
      mutation.mutate({ custom_name: newCustomName });
    }
  }, [draft, activity.activity_name, activity.custom_name, mutation]);

  function cancel() {
    savingRef.current = true; // prevent blur from saving
    setEditing(false);
    setDraft(displayName);
  }

  // Show optimistic name while mutation is pending
  const shownName = mutation.isPending
    ? (mutation.variables?.custom_name ?? activity.activity_name ?? "Activity")
    : displayName;

  return (
    <div className="space-y-2">
      <Button
        variant="ghost"
        size="sm"
        className="gap-1 text-muted-foreground"
        onClick={() => router.push("/dashboard")}
      >
        <ArrowLeft className="h-4 w-4" />
        Dashboard
      </Button>
      <div className="flex items-center gap-3 flex-wrap">
        {editing ? (
          <Input
            ref={inputRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") save();
              if (e.key === "Escape") cancel();
            }}
            onBlur={save}
            className="text-2xl font-bold h-auto py-0 px-1 max-w-md"
          />
        ) : (
          <h1
            className="text-2xl font-bold cursor-pointer group flex items-center gap-2"
            onClick={startEditing}
            title="Click to rename"
          >
            {shownName}
            <Pencil className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </h1>
        )}
        <Badge variant="secondary">
          {activityTypeLabel(activity.activity_type)}
        </Badge>
        {activity.pr && (
          <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20">
            <Trophy className="h-3 w-3 mr-1" />
            PR
          </Badge>
        )}
        {activity.favorite && (
          <Badge className="bg-pink-500/10 text-pink-500 border-pink-500/20">
            <Star className="h-3 w-3 mr-1" />
            Favorite
          </Badge>
        )}
      </div>
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>{formatDate(activity.start_timestamp)}</span>
        {activity.device_name && (
          <span className="flex items-center gap-1">
            <Watch className="h-3.5 w-3.5" />
            {activity.device_name}
          </span>
        )}
      </div>
      {activity.description && (
        <p className="text-sm text-muted-foreground bg-accent/30 rounded-md px-3 py-2 mt-2">
          {activity.description}
        </p>
      )}
    </div>
  );
}
