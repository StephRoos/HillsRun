"use client";

import { useState } from "react";
import { Pencil, X, Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useVma, useUpdateVma } from "@/hooks/use-vma";

export function VmaCard() {
  const { data, isPending, isError } = useVma();
  const updateVma = useUpdateVma();
  const [editing, setEditing] = useState(false);
  const [inputValue, setInputValue] = useState("");

  if (isError) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">VMA</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Could not load data</p>
        </CardContent>
      </Card>
    );
  }

  if (isPending) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-16" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-8 w-24 mx-auto" />
          <Skeleton className="h-4 w-16 mx-auto" />
        </CardContent>
      </Card>
    );
  }

  const isManual = data?.manual_vma != null;
  const displayValue = data?.manual_vma ?? data?.estimated_vma;
  const vo2max = data?.vo2_max;

  function vmaToPace(vma: number): string {
    const minPerKm = 60 / vma;
    const mins = Math.floor(minPerKm);
    const secs = Math.round((minPerKm - mins) * 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  }

  function startEditing() {
    setInputValue(displayValue?.toString() ?? "");
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
    setInputValue("");
  }

  function saveVma() {
    const parsed = parseFloat(inputValue);
    if (!inputValue || isNaN(parsed) || parsed < 5 || parsed > 30) return;
    updateVma.mutate(parsed, { onSuccess: () => setEditing(false) });
  }

  function clearManualVma() {
    updateVma.mutate(null, { onSuccess: () => setEditing(false) });
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium">VMA</CardTitle>
        {!editing && (
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={startEditing} aria-label="Edit VMA">
            <Pencil className="h-3.5 w-3.5" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {editing ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Input
                type="number"
                step="0.1"
                min="5"
                max="30"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder="km/h"
                className="h-8 text-center"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveVma();
                  if (e.key === "Escape") cancelEditing();
                }}
              />
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={saveVma} disabled={updateVma.isPending}>
                <Check className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={cancelEditing}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            {isManual && (
              <Button
                variant="outline"
                size="sm"
                className="w-full text-xs"
                onClick={clearManualVma}
                disabled={updateVma.isPending}
              >
                Use estimate
              </Button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-1">
            {vo2max != null && (
              <span className="text-xs text-muted-foreground">
                VO2max {vo2max}
              </span>
            )}
            <span className="text-2xl font-bold">
              {displayValue != null ? `${displayValue} km/h` : "—"}
            </span>
            {displayValue != null && (
              <>
                <Badge variant="secondary" className="text-[10px]">
                  {isManual ? "manual" : "estimated"}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {vmaToPace(displayValue)} min/km
                </span>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
