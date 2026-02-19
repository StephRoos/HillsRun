"use client";

import { useState } from "react";
import { Plus, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TrainingCalendar } from "@/components/calendar/training-calendar";
import { ImportDialog } from "@/components/calendar/import-dialog";

export default function CalendarPage() {
  const [importOpen, setImportOpen] = useState(false);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Training Calendar</h1>
        <Button
          variant="outline"
          size="sm"
          className="gap-2"
          onClick={() => setImportOpen(true)}
        >
          <Upload className="h-4 w-4" />
          Import CSV
        </Button>
      </div>

      <TrainingCalendar />

      <ImportDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  );
}
