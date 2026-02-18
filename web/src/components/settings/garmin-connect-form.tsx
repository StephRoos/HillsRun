"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useConnectGarmin, useSubmitMfa } from "@/hooks/use-garmin-account";
import { Loader2 } from "lucide-react";

export function GarminConnectForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaSessionId, setMfaSessionId] = useState<string | null>(null);

  const connectMutation = useConnectGarmin();
  const mfaMutation = useSubmitMfa();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email || !password) return;
    connectMutation.mutate(
      { email, password },
      {
        onSuccess: (data) => {
          if (data.needs_mfa && data.mfa_session_id) {
            setMfaSessionId(data.mfa_session_id);
          }
        },
      }
    );
  }

  function handleMfaSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!mfaSessionId || !mfaCode) return;
    mfaMutation.mutate({ mfa_session_id: mfaSessionId, mfa_code: mfaCode });
  }

  const isPending = connectMutation.isPending || mfaMutation.isPending;

  // MFA step
  if (mfaSessionId) {
    return (
      <form onSubmit={handleMfaSubmit} className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Enter the verification code from your authenticator app or SMS.
        </p>
        <div className="space-y-2">
          <Label htmlFor="mfa-code">Verification code</Label>
          <Input
            id="mfa-code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
            placeholder="123456"
            disabled={mfaMutation.isPending}
            autoFocus
          />
        </div>
        <div className="flex gap-2">
          <Button
            type="submit"
            size="sm"
            disabled={mfaMutation.isPending || !mfaCode}
          >
            {mfaMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              "Verify"
            )}
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setMfaSessionId(null);
              setMfaCode("");
            }}
            disabled={mfaMutation.isPending}
          >
            Cancel
          </Button>
        </div>
      </form>
    );
  }

  // Credentials step
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
          disabled={isPending}
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
          disabled={isPending}
        />
      </div>
      <Button
        type="submit"
        size="sm"
        disabled={isPending || !email || !password}
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
