"use client";

import { BarChart2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ChartErrorFallbackProps {
  onRetry?: () => void;
}

export function ChartErrorFallback({ onRetry }: ChartErrorFallbackProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center justify-center gap-3 py-10 text-center">
        <BarChart2 className="h-8 w-8 text-muted-foreground opacity-40" />
        <p className="text-sm text-muted-foreground">
          Impossible de charger le graphique.
        </p>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            Réessayer
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
