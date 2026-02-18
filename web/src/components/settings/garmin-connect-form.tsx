"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useConnectGarmin } from "@/hooks/use-garmin-account";
import { Loader2 } from "lucide-react";

export function GarminConnectForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const connectMutation = useConnectGarmin();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    connectMutation.mutate({ email, password });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Enter your Garmin Connect credentials to sync your fitness data.
        Your credentials are used once to obtain an authentication token and are never stored.
      </p>
      <div className="space-y-2">
        <Label htmlFor="garmin-email">Garmin email</Label>
        <Input
          id="garmin-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          disabled={connectMutation.isPending}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="garmin-password">Garmin password</Label>
        <Input
          id="garmin-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Your Garmin password"
          disabled={connectMutation.isPending}
        />
      </div>
      <Button
        type="submit"
        size="sm"
        disabled={connectMutation.isPending || !email || !password}
      >
        {connectMutation.isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Connecting...
          </>
        ) : (
          "Connect Garmin"
        )}
      </Button>
    </form>
  );
}
