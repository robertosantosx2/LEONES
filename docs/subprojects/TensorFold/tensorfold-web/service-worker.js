"use strict";

const CACHE_NAME = "tensorfold-web-shell-v1";
const SHELL_URLS = [
  "/",
  "/manifest.webmanifest",
  "/tensorfold-web-icon.svg"
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys
        .filter(key => key.startsWith("tensorfold-web-shell-") && key !== CACHE_NAME)
        .map(key => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  // Engine health, models, chat/SSE, process controls, stats and dashboard are live APIs.
  if (url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put("/", copy));
        }
        return response;
      }).catch(async () => (await caches.match("/")) ||
        new Response("TensorFold Web is offline. Start the local bridge to use Engine features.", {
          status: 503,
          headers: { "Content-Type": "text/plain; charset=utf-8" }
        }))
    );
    return;
  }

  if (!SHELL_URLS.includes(url.pathname)) return;
  event.respondWith(
    caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
      }
      return response;
    }))
  );
});
