import { defaultCache } from "@serwist/next/worker";
import type { PrecacheEntry, SerwistGlobalConfig } from "serwist";
import {
  ExpirationPlugin,
  NetworkFirst,
  NetworkOnly,
  Serwist,
  StaleWhileRevalidate,
} from "serwist";

declare global {
  interface WorkerGlobalScope extends SerwistGlobalConfig {
    __SW_MANIFEST: (PrecacheEntry | string)[] | undefined;
  }
}

declare const self: ServiceWorkerGlobalScope;

const serwist = new Serwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    // Never cache auth routes
    {
      matcher: /\/api\/auth\/.*/i,
      handler: new NetworkOnly(),
    },
    // Garmin API data — NetworkFirst with 4h cache
    {
      matcher: /\/api\/garmin\/.*/i,
      handler: new NetworkFirst({
        cacheName: "garmin-api",
        networkTimeoutSeconds: 10,
        plugins: [
          new ExpirationPlugin({
            maxAgeSeconds: 4 * 60 * 60,
            maxEntries: 100,
          }),
        ],
      }),
    },
    // Images — StaleWhileRevalidate
    {
      matcher: /\.(?:png|jpg|jpeg|svg|gif|webp|ico)$/i,
      handler: new StaleWhileRevalidate({
        cacheName: "images",
        plugins: [
          new ExpirationPlugin({
            maxEntries: 100,
            maxAgeSeconds: 30 * 24 * 60 * 60,
          }),
        ],
      }),
    },
    // Default caching rules from Serwist
    ...defaultCache,
  ],
  fallbacks: {
    entries: [
      {
        url: "/~offline",
        matcher({ request }) {
          return request.destination === "document";
        },
      },
    ],
  },
});

serwist.addEventListeners();
