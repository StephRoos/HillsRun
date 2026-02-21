import { betterAuth } from "better-auth";
import { createAuthMiddleware } from "better-auth/api";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { prisma } from "./prisma";

const GARMIN_API_BASE = process.env.GARMIN_API_URL;
const GARMIN_API_KEY = process.env.GARMIN_API_KEY;

export const auth = betterAuth({
  database: prismaAdapter(prisma, {
    provider: "postgresql",
  }),
  emailAndPassword: {
    enabled: true,
  },
  hooks: {
    after: createAuthMiddleware(async (ctx) => {
      // Only trigger sync on actual credential sign-in/sign-up, not session checks
      const isSignUp = ctx.path === "/sign-up/email";
      const isSignIn = ctx.path === "/sign-in/email";
      const isSuccess =
        (ctx.context?.returned as Response | undefined)?.status === 200;

      if ((isSignIn || isSignUp) && isSuccess) {
        let betterAuthUserId: string | undefined;
        try {
          const returned = ctx.context?.returned as Response | undefined;
          if (returned && typeof returned.clone === "function") {
            const body = await returned.clone().json();
            betterAuthUserId = body?.user?.id;
          }
        } catch {
          // Ignore parse errors
        }

        const syncBody = isSignUp
          ? { mode: "full", days_back: 365, better_auth_user_id: betterAuthUserId }
          : { better_auth_user_id: betterAuthUserId };

        fetch(`${GARMIN_API_BASE}/api/v1/sync/trigger`, {
          method: "POST",
          headers: {
            "X-API-Key": GARMIN_API_KEY ?? "",
            "Content-Type": "application/json",
          },
          body: JSON.stringify(syncBody),
        }).catch(() => {});
      }
    }),
  },
});
