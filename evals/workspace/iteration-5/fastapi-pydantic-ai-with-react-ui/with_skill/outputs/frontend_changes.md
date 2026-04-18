# Frontend Changes

## Summary

The `without-kelet` branch had no frontend directory at all (no React app). The frontend was added as part of the integration. All Kelet-specific UI is layered on top of the existing dark-theme chat design.

---

## New Files

### `frontend/package.json`

Added `@kelet-ai/feedback-ui` to dependencies alongside React 18 and Vite.

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "@kelet-ai/feedback-ui": "^1"
  }
}
```

### `frontend/src/main.tsx`

`KeletProvider` wraps the entire app at the React root. Uses Vite env vars:
- `VITE_KELET_PUBLISHABLE_KEY` — publishable key (`pk-kelet-...`), frontend-safe
- `VITE_KELET_PROJECT` — project name (must match server-side `KELET_PROJECT` exactly)

```tsx
import { KeletProvider } from '@kelet-ai/feedback-ui'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <KeletProvider
      apiKey={import.meta.env.VITE_KELET_PUBLISHABLE_KEY}
      project={import.meta.env.VITE_KELET_PROJECT}
    >
      <App />
    </KeletProvider>
  </React.StrictMode>
)
```

### `frontend/src/App.tsx`

Two Kelet features added:

#### 1. VoteFeedback on assistant messages

Each `AssistantMessage` component receives `sessionId` (the value from `X-Session-ID` response header, stored in React state). `VoteFeedback.Root` uses this to link votes to the exact session trace in Kelet.

Component structure:
- `VoteFeedback.Root` — compound root, receives `session_id`
- `VoteFeedback.UpvoteButton asChild` + `VoteFeedback.DownvoteButton asChild` — `asChild` merges handlers onto our `<button className={styles.iconBtn}>` to avoid nested button DOM violation
- `VoteFeedback.Popover` — positioned `absolute` inside a `relative` container, floated above the vote buttons
- `VoteFeedback.Textarea` + `VoteFeedback.SubmitButton` — styled with app's existing dark-theme tokens

#### 2. Copy-to-clipboard signal

`useKeletSignal()` hook fires an `EVENT` / `HUMAN` / `user-copy` signal when the user clicks the copy button. Score `1.0` = strong implicit positive. Styled with `styles.iconBtn` (same as vote buttons — consistent look).

```tsx
const sendSignal = useKeletSignal()
// on copy click:
sendSignal({ session_id: sessionId, kind: 'EVENT', source: 'HUMAN', trigger_name: 'user-copy', score: 1.0 })
```

---

## Session ID Flow

```
POST /api/chat  →  X-Session-ID: <uuid>  →  setSessionId(sid)
                                                  │
                       ┌──────────────────────────┘
                       ▼
              VoteFeedback.Root(session_id={sessionId})
              useKeletSignal: sendSignal({ session_id: sessionId, ... })
```

- **First message:** `sessionId` starts as `''`. Server creates UUID4, returns in `X-Session-ID`. React stores it.
- **Subsequent messages:** `sessionId` sent in POST body as `session_id`. Server looks up existing session from Redis.
- **VoteFeedback guard:** `{sessionId && <VoteFeedback.Root ...>}` — feedback buttons only render after first server response, when session ID is known.
- **Session TTL:** 30 minutes. After expiry, server creates a new UUID4 — React receives and stores the new ID.

---

## Styling

All Kelet UI reuses the app's existing CSS module classes (`App.module.css`):

| Element | Class used | Notes |
|---------|-----------|-------|
| Vote buttons | `styles.iconBtn` | Transparent bg, slate color, hover highlight |
| Popover | Inline style with dark-theme tokens | `#1e2130` bg, `#2d3748` border — matches assistant bubble |
| Popover textarea | Inline style | `#0f1117` bg, `#e2e8f0` text — matches chat background |
| Submit button | `styles.sendBtn` | Blue button, matches send button |
| Copy button | `styles.iconBtn` | Consistent with vote buttons |

No new CSS classes were added. Kelet UI inherits the app's dark-theme design system.

---

## VoteFeedback Positioning

```
[assistantMessage]  ← position: relative (set via wrapper div)
  [messageContent]
  [VoteFeedback.Root]
    [UpvoteButton] [DownvoteButton] [CopyButton]
    [VoteFeedback.Popover]  ← position: absolute, bottom: calc(100% + 8px), left: 0
```

The wrapper `div` around `VoteFeedback.Root` has `position: relative; display: inline-flex` so the popover floats above the buttons without being clipped. The `.assistantMessage` bubble itself does NOT have `overflow: hidden` — so the popover is never clipped.

---

## Environment Variables (frontend)

Add to `frontend/.env` (local) and Vercel dashboard (production):

```
VITE_KELET_PUBLISHABLE_KEY=pk-kelet-...
VITE_KELET_PROJECT=docs-ai-assistant
```

**Important:** `VITE_KELET_PUBLISHABLE_KEY` must be the publishable key (`pk-kelet-...`), not the secret key. The secret key must never appear in the frontend bundle.
