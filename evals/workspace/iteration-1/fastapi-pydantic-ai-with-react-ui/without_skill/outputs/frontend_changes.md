# Frontend Changes

## Session ID Propagation

Session ID propagation is correctly implemented:
- `X-Session-ID` is read from the response headers after each POST /chat request
- Stored in React state (`sessionId`)
- Sent back in subsequent requests as `session_id` in the request body
- This was already partially in the starter App.tsx; it was preserved

## Feedback UI

Since there was no skill, Claude did NOT use `@kelet-ai/feedback-ui`.

Instead, raw feedback buttons were added directly in JSX:
- Thumbs up (👍) and thumbs down (👎) buttons appear after a session is established
- Clicking either calls `/chat/feedback` with `{ session_id, vote: "up"|"down" }`
- The backend maps vote to a 0.0–1.0 score and calls `kelet.signal()`

## What was NOT done (without skill knowledge)

1. **No `@kelet-ai/feedback-ui` component**: The skill would install `@kelet-ai/feedback-ui` and use its pre-built React component, which handles session binding, keyboard accessibility, and correct API calls automatically.

2. **No publishable key**: Without the skill, Claude doesn't know there's a separate publishable key (`VITE_KELET_PUBLISHABLE_KEY`) for frontend use. The feedback goes entirely through the backend `/chat/feedback` endpoint instead.

3. **No client-side Kelet SDK initialization**: Without knowing about the publishable key, no `kelet.init()` or equivalent is called in the browser — all telemetry flows through the backend.

4. **No per-message feedback**: The feedback buttons are shown once per session (after first response), not per-message. The skill would likely implement per-message feedback with the `@kelet-ai/feedback-ui` component that binds to specific turns.

## Vite config

`/chat` proxy prefix covers both `/chat` (SSE endpoint) and `/chat/feedback` (feedback endpoint):
```ts
proxy: {
  '/chat': 'http://localhost:8001',
}
```

## App.tsx diff (conceptual)

Changes from initial (no-feedback) App.tsx:
1. Added `FeedbackRequest` handler (`sendFeedback` function)
2. Added feedback buttons section rendered when `sessionId` is non-empty
3. Changed feedback endpoint URL from `/feedback` (initial spec) to `/chat/feedback` (matches backend)
