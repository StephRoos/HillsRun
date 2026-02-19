"use client";

import { useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Upload } from "lucide-react";
import { useImportPlannedWorkouts } from "@/hooks/use-planned-workouts";

interface ImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function downloadTemplate() {
  const csv = `date,sport_type,title,description,duration_minutes,distance_km,intensity
2026-03-01,running,Easy run,,45,10,easy
2026-03-02,strength_training,Upper body,Gym session,60,,moderate
2026-03-03,rest,Rest day,,,,
2026-03-04,trail_running,Long trail,,120,25,hard`;

  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "planned_workouts_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export function ImportDialog({ open, onOpenChange }: ImportDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string[][]>([]);
  const [result, setResult] = useState<{
    imported: number;
    errors: string[];
  } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const importMutation = useImportPlannedWorkouts();

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setResult(null);

    const reader = new FileReader();
    reader.onload = (ev) => {
      const text = ev.target?.result as string;
      const lines = text.split("\n").filter((l) => l.trim());
      const rows = lines.map((l) => l.split(","));
      setPreview(rows.slice(0, 6)); // header + 5 rows
    };
    reader.readAsText(f);
  }

  function handleImport() {
    if (!file) return;
    importMutation.mutate(file, {
      onSuccess: (data) => {
        setResult(data);
        setFile(null);
        if (data.errors.length === 0) {
          setTimeout(() => onOpenChange(false), 1500);
        }
      },
    });
  }

  function handleClose(open: boolean) {
    if (!open) {
      setFile(null);
      setPreview([]);
      setResult(null);
    }
    onOpenChange(open);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Import Training Plan</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <Button
            variant="outline"
            size="sm"
            onClick={downloadTemplate}
            className="gap-2"
          >
            <Download className="h-4 w-4" />
            Download CSV Template
          </Button>

          <div>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileRef.current?.click()}
              className="gap-2"
            >
              <Upload className="h-4 w-4" />
              {file ? file.name : "Select CSV file"}
            </Button>
          </div>

          {preview.length > 0 && (
            <div className="overflow-x-auto border rounded-md">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-muted">
                    {preview[0]?.map((h, i) => (
                      <th key={i} className="px-2 py-1 text-left font-medium">
                        {h.trim()}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.slice(1).map((row, i) => (
                    <tr key={i} className="border-t">
                      {row.map((cell, j) => (
                        <td key={j} className="px-2 py-1 text-muted-foreground">
                          {cell.trim()}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {result && (
            <div className="space-y-2 text-sm">
              <p className="text-green-500">
                Imported {result.imported} workouts
              </p>
              {result.errors.length > 0 && (
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {result.errors.map((err, i) => (
                    <p key={i} className="text-red-500 text-xs">
                      {err}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleClose(false)}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleImport}
            disabled={!file || importMutation.isPending}
          >
            {importMutation.isPending ? "Importing..." : "Import"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
