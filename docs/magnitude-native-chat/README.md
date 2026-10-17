# Magnitude Native Chat — implementation brief

**Branch:** `feat/magnitude-native-chat`  
**Target:** `magnitudedev/magnitude`  
**Working repository:** `robertosantosx2/LEONES`  
**Status:** design + prototype; upstream implementation/CI still required.

## Goal

Make local inference directly usable from Magnitude's own interface, with a first-class **Chat** destination, without changing the existing inference service contract or removing its model-management screens.

## What ODS contributes

ODS deliberately separates the conversational surface from administration: Open WebUI provides chat, while the ODS dashboard manages models and services. The transferable patterns are:

- a conversation-first layout with a history sidebar;
- a clear, persistent model selector;
- streaming assistant output and a stop action;
- obvious empty, loading, and error states;
- local-first behavior and responsive layout.

We should reproduce those interaction principles, not copy ODS/Open WebUI implementation or branding. Magnitude should keep its own slate/blue palette, typography, React/Tailwind primitives, and current navigation conventions.

## Current Magnitude contract

The current web app is served by the Magnitude service at `http://127.0.0.1:10100`. The local inference API is available at `/inference/v1`:

- `GET /inference/v1/models` — exact model IDs for the selector.
- `POST /inference/v1/chat/completions` — JSON or server-sent-event streaming.

The existing app navigation is declared by `ApplicationPage` in `packages/client-common/src/application/contracts.ts`; the page list and navigation are rendered in `web/src/app.tsx`. A new Chat destination must be integrated there rather than bolted on as a separate Python server.

## Port decision: 10101 without breaking 10100

Keep the current ACN/API listener on `127.0.0.1:10100` as the canonical service endpoint. Expose the chat entry at `http://127.0.0.1:10101/` through an explicit, lifecycle-managed local web listener/alias that serves the same built Magnitude web assets with the Chat route as its landing page and proxies only same-origin UI requests to the canonical local service. It must bind to loopback by default, report a clear startup error if 10101 is occupied, and never silently change the API port. Do not add an unrelated always-running server or require a second Python process.

Before implementation, maintainers should confirm whether a second listener is acceptable or prefer the existing app on 10100 with `/chat` as the canonical route and a documented local redirect. This is the principal architecture question for review.

## UX scope

1. **Chat navigation:** first-class sidebar item, keyboard accessible and responsive.
2. **Model selector:** populated from the live `/inference/v1/models` response using exact IDs; refresh/retry states; no fabricated default if no models exist.
3. **Conversation history:** local browser storage, newest activity first, rename/delete/new conversation, persist model ID and messages. No account or cloud dependency.
4. **Streaming:** request `stream: true`; parse SSE incrementally; append deltas as they arrive; handle `[DONE]`; preserve partial output on failure; stop/cancel via AbortController.
5. **Composer:** Enter to send, Shift+Enter for newline, disabled/working states, empty-prompt validation, stop while generating.
6. **Safety and privacy:** local-only storage, no telemetry of prompt content, no external provider fallback, escape/render plain text safely, no HTML injection.
7. **Failure states:** API unavailable, no models, selected model unavailable, malformed SSE, aborted request, quota/context/runtime error.
8. **Visual system:** reuse Magnitude's existing Button/Input/Select primitives, icon library, slate/blue palette, dark/light/system appearance and narrow viewport navigation.
9. **Accessibility:** semantic landmarks, labels, visible focus, polite live region for streaming, reduced-motion support.
10. **Documentation:** explain local history, port behavior, API requests, data deletion and troubleshooting.

## Non-goals for v1

- RAG, file uploads, web search, voice, tools, agents, cloud providers, cross-device sync, or account-backed conversations.
- Changing the inference engine's default model, backend selection, or API behavior.
- Replacing Discover, Catalog, My Models, Connections, Usage, Status or Settings.

## Proposed implementation sequence

1. Add `chat` to the shared `ApplicationPage` schema and page navigation.
2. Add a small isolated `web/src/components/chat-page.tsx` and focused unit tests for SSE parsing, persistence, and error handling.
3. Integrate the component into `web/src/app.tsx`, reusing Magnitude UI primitives.
4. Add lifecycle-managed loopback access on 10101 only if maintainers approve the second listener; otherwise use 10100/chat and document the URL decision.
5. Add tests for exact model IDs, empty catalog, streamed multi-chunk response, `[DONE]`, abort, malformed stream, localStorage recovery and mobile layout.
6. Run formatter, typecheck, unit tests, web build, relevant ACN/server tests and manual local inference smoke test.
7. Submit a focused PR to `magnitudedev/magnitude`; keep this LEONES branch as the research record/prototype, not as a dependency.

## Acceptance criteria

- [ ] Chat is visible in the Magnitude navigation and opens a usable empty state.
- [ ] Model list is fetched from the live local API; selection uses the exact API model ID.
- [ ] Assistant text appears incrementally, not only after the response completes.
- [ ] Stop aborts the in-flight HTTP request and leaves coherent history.
- [ ] Conversations survive a reload in the same browser and can be deleted.
- [ ] Errors are actionable; there is no silent fallback to cloud.
- [ ] Existing model/catalog/settings flows remain unchanged.
- [ ] Port 10100 API remains healthy; 10101 binds to loopback only and has deterministic collision behavior.
- [ ] Tests and build pass; actual inference smoke test is explicitly distinguished from mocked tests.
- [ ] PR documents limitations and any unrun checks.

## References

- Magnitude web app: https://github.com/magnitudedev/magnitude
- Magnitude local inference API: https://github.com/magnitudedev/magnitude/blob/main/docs/api/endpoints.mdx
- Magnitude web client design: https://github.com/magnitudedev/magnitude/blob/main/design/clients/web-local-inference.md
- ODS project: https://github.com/Osmantic/ODS
- ODS quick start (chat/dashboard separation): https://github.com/Osmantic/ODS/blob/main/ods/QUICKSTART.md
