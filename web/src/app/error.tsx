"use client";

import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4 p-6">
      <AlertTriangle className="h-12 w-12 text-destructive" />
      <h2 className="text-xl font-semibold">Quelque chose s&apos;est mal passé</h2>
      <p className="text-sm text-muted-foreground text-center max-w-md">
        {error.message || "Une erreur inattendue est survenue."}
      </p>
      <Button onClick={reset}>Réessayer</Button>
    </div>
  );
}
