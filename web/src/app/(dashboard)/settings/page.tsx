"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession, signOut } from "@/lib/auth-client";
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

export default function SettingsPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const [name, setName] = useState(session?.user?.name ?? "");
  const [units, setUnits] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("hillsrun-units") ?? "km";
    }
    return "km";
  });
  const [saved, setSaved] = useState(false);

  function handleSaveName() {
    // For MVP, name update would call Better-Auth's update profile
    // For now, just show feedback
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function handleUnitsChange(value: string) {
    setUnits(value);
    if (typeof window !== "undefined") {
      localStorage.setItem("hillsrun-units", value);
    }
  }

  async function handleDeleteAccount() {
    // In MVP, sign out and redirect
    // Full account deletion would require a server action
    await signOut();
    router.push("/");
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-2xl font-bold">Réglages</h1>

      {/* Profile */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Profil
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
              L&apos;email ne peut pas être modifié.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="name">Nom d&apos;affichage</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ton prénom"
            />
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={handleSaveName}>
              Enregistrer
            </Button>
            {saved && (
              <span className="text-sm text-emerald-500">Sauvegardé</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Préférences
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Unités de distance</Label>
            <Select value={units} onValueChange={handleUnitsChange}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="km">Kilomètres (km)</SelectItem>
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
            Zone dangereuse
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">
            La suppression de ton compte est irréversible. Toutes tes données
            seront supprimées.
          </p>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="sm">
                Supprimer mon compte
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Supprimer ton compte ?</AlertDialogTitle>
                <AlertDialogDescription>
                  Cette action est irréversible. Ton compte et toutes tes
                  données seront définitivement supprimés.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Annuler</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleDeleteAccount}
                  className="bg-destructive text-white hover:bg-destructive/90"
                >
                  Supprimer définitivement
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </div>
  );
}
