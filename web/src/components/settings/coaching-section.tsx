"use client";

import { useState } from "react";
import { Copy, Trash2, UserMinus, Link2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  useCoachingStatus,
  useGenerateInviteCode,
  useInviteCodes,
  useRevokeInviteCode,
  useRedeemInviteCode,
  useRemoveAthlete,
  useRemoveCoach,
} from "@/hooks/use-coaching";

export function CoachingSection() {
  const { data: status } = useCoachingStatus();
  const [redeemCode, setRedeemCode] = useState("");

  const generateCode = useGenerateInviteCode();
  const inviteCodes = useInviteCodes();
  const revokeCode = useRevokeInviteCode();
  const redeemInvite = useRedeemInviteCode();
  const removeAthlete = useRemoveAthlete();
  const removeCoach = useRemoveCoach();

  function copyCode(code: string) {
    navigator.clipboard.writeText(code);
    toast.success("Code copied to clipboard");
  }

  return (
    <>
      {/* Coaching card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Coaching</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Generate an invite code and share it with an athlete so they can
              link their account to you.
            </p>
            <Button
              size="sm"
              onClick={() => generateCode.mutate()}
              disabled={generateCode.isPending}
            >
              {generateCode.isPending ? "Generating..." : "Generate invite code"}
            </Button>
          </div>

          {/* Invite codes list */}
          {inviteCodes.data && inviteCodes.data.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase">
                Invite codes
              </p>
              {inviteCodes.data.map((ic) => (
                <div
                  key={ic.id}
                  className="flex items-center justify-between rounded-md border p-2 text-sm"
                >
                  <div className="flex items-center gap-2">
                    <code className="font-mono text-sm">{ic.code}</code>
                    <Badge
                      variant={
                        ic.status === "pending"
                          ? "outline"
                          : ic.status === "redeemed"
                            ? "default"
                            : "secondary"
                      }
                    >
                      {ic.status}
                    </Badge>
                  </div>
                  <div className="flex gap-1">
                    {ic.status === "pending" && (
                      <>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => copyCode(ic.code)}
                        >
                          <Copy className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive"
                          onClick={() => revokeCode.mutate(ic.code)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Athletes list */}
          {status?.athletes && status.athletes.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase">
                Your athletes
              </p>
              {status.athletes.map((a) => (
                <div
                  key={a.athlete_user_id}
                  className="flex items-center justify-between rounded-md border p-2 text-sm"
                >
                  <span>{a.display_name || a.email || `User #${a.athlete_user_id}`}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={() => removeAthlete.mutate(a.athlete_user_id)}
                  >
                    <UserMinus className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* My Coaches card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">My Coaches</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Enter invite code"
              value={redeemCode}
              onChange={(e) => setRedeemCode(e.target.value.toUpperCase())}
              className="font-mono uppercase w-48"
            />
            <Button
              size="sm"
              disabled={!redeemCode.trim() || redeemInvite.isPending}
              onClick={() => {
                redeemInvite.mutate(redeemCode.trim(), {
                  onSuccess: () => setRedeemCode(""),
                });
              }}
            >
              <Link2 className="mr-2 h-4 w-4" />
              Link
            </Button>
          </div>

          {status?.coaches && status.coaches.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase">
                Active coaches
              </p>
              {status.coaches.map((c) => (
                <div
                  key={c.coach_better_auth_id}
                  className="flex items-center justify-between rounded-md border p-2 text-sm"
                >
                  <span>{c.coach_name || c.coach_email || "Coach"}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive"
                    onClick={() => removeCoach.mutate(c.coach_better_auth_id)}
                  >
                    <UserMinus className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
