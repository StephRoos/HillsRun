"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut, authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { GarminConnectForm } from "@/components/settings/garmin-connect-form";
import {
  useGarminAccount,
  useDisconnectGarmin,
} from "@/hooks/use-garmin-account";
import { useTriggerSync } from "@/hooks/use-sync";
import { Loader2 } from "lucide-react";
import { CoachingSection } from "@/components/settings/coaching-section";

export default function SettingsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const [name, setName] = useState(session?.user?.name ?? "");
  const [saving, setSaving] = useState(false);
  const { trigger: triggerSync, isSyncing: syncing } = useTriggerSync();
  const [units, setUnits] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("hillsrun-units") ?? "km";
    }
    return "km";
  });

  const { data: garminAccount, isLoading: garminLoading } =
    useGarminAccount();
  const disconnectMutation = useDisconnectGarmin();

  async function handleSaveName() {
    setSaving(true);
    try {
      await authClient.updateUser({ name });
      toast.success("Display name updated");
    } catch {
      toast.error("Failed to update display name");
    } finally {
      setSaving(false);
    }
  }

  function handleUnitsChange(value: string) {
    setUnits(value);
    if (typeof window !== "undefined") {
      localStorage.setItem("hillsrun-units", value);
    }
    toast.success(`Units set to ${value === "km" ? "kilometers" : "miles"}`);
  }

  function handleSyncNow(full = false) {
    triggerSync(full ? { mode: "full", days_back: 365 } : undefined);
  }

  async function handleDeleteAccount() {
    try {
      await authClient.deleteUser();
      toast.success("Account deleted");
      router.push("/");
    } catch {
      // Fallback: sign out if deletion not supported
      await signOut();
      router.push("/");
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Profile
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Email</Label>
            <Input
              value={session?.user?.email ?? ""}
              disabled
              className="opacity-60"
            />
            <p className="text-xs text-muted-foreground">
              Email cannot be changed.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Display name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your first name"
            />
          </div>
          <Button size="sm" onClick={handleSaveName} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </Button>
        </CardContent>
      </Card>

      {/* Garmin Account */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Garmin Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          {garminLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading...
            </div>
          ) : garminAccount?.connected ? (
            <div className="space-y-4">
              <div className="space-y-1">
                <p className="text-sm">
                  Connected as{" "}
                  <span className="font-medium">
                    {garminAccount.garmin_display_name}
                  </span>
                </p>
                {garminAccount.last_sync && (
                  <p className="text-xs text-muted-foreground">
                    Last sync:{" "}
                    {new Date(garminAccount.last_sync).toLocaleString()}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSyncNow(false)}
                  disabled={syncing}
                >
                  {syncing ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Syncing...
                    </>
                  ) : (
                    "Sync now"
                  )}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleSyncNow(true)}
                  disabled={syncing}
                >
                  Full sync
                </Button>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={disconnectMutation.isPending}
                    >
                      Disconnect
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        Disconnect Garmin account?
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        Your synced data will remain but no new data will be
                        fetched. You can reconnect anytime.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => disconnectMutation.mutate()}
                      >
                        Disconnect
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          ) : (
            <GarminConnectForm />
          )}
        </CardContent>
      </Card>

      {/* Coaching */}
      <CoachingSection />

      {/* Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Preferences
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Distance units</Label>
            <Select value={units} onValueChange={handleUnitsChange}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="km">Kilometers (km)</SelectItem>
                <SelectItem value="mi">Miles (mi)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Danger zone */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-destructive">
            Danger zone
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Deleting your account is irreversible. All your data will be deleted.
          </p>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm">
                Delete my account
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete your account?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action is irreversible. Your account and all your data will be permanently deleted.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDeleteAccount}
                  className="bg-destructive text-white hover:bg-destructive/90"
                >
                  Delete permanently
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
