import { betterAuth } from "better-auth";
import { createAuthMiddleware } from "better-auth/api";
import { prismaAdapter } from "better-auth/adapters/prisma";
import { prisma } from "./prisma";

const GARMIN_API_BASE = process.env.NEXT_PUBLIC_GARMIN_API_URL;
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
      if (ctx.path.startsWith("/sign-in")) {
        // Fire-and-forget sync trigger on login
        fetch(`${GARMIN_API_BASE}/api/v1/sync/trigger`, {
          method: "POST",
          headers: {
            "X-API-Key": GARMIN_API_KEY ?? "",
            "Content-Type": "application/json",
          },
          body: "{}",
        }).catch(() => {
          // Silently ignore errors (409 = sync already running, network issues, etc.)
        });
      }
    }),
  },
});
