# Frontend Changes

## Summary

The app had no feedback UI at all before integration — plain chat with user/assistant messages and a text input. The skill added Kelet's feedback layer on top of the existing visual style without replacing any components.

---

## Package Changes

`frontend/package.json` — added `@kelet-ai/feedback-ui: ^1`:

```json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "@kelet-ai/feedback-ui": "^1"
  }
}
```

---

## New File: `frontend/.env`

```
VITE_KELET_PUBLISHABLE_KEY=pk-kelet-...
VITE_KELET_PROJECT=docs-ai-assistant
```

Publishable key only — secret key stays in root `.env` (server-side).

---

## `frontend/src/main.tsx` — KeletProvider at root

Wrapped the entire app in `KeletProvider` so all child components can use `VoteFeedback` and `useKeletSignal`:

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

---

## `frontend/src/App.tsx` — Feedback UI + signals

### New component: `AssistantMessage`

Extracted assistant message rendering into a dedicated component that carries the `sessionId` prop. Each assistant message now renders:

1. **VoteFeedback thumbs (up/down)** — attached to the session that produced this message. Uses `asChild` pattern to avoid nested `<button>` elements (SKILL rule: never return a `<button>` from render prop without `asChild`).
2. **Feedback popover** — floats above the buttons using `position: absolute` on the popover and `position: relative` on the wrapping container.
3. **Copy button** — fires a `user-copy` EVENT signal on click.

```tsx
function AssistantMessage({ content, sessionId }) {
  const sendSignal = useKeletSignal()

  // VoteFeedback uses asChild to avoid nested buttons
  <VoteFeedback.UpvoteButton asChild>
    <button className={styles.iconBtn}>▲</button>
  </VoteFeedback.UpvoteButton>
  
  // Popover has absolute positioning; wrapper has position:relative
  <div style={{ position: 'relative', ... }}>
    <VoteFeedback.Root session_id={sessionId}>
      ...
      <VoteFeedback.Popover style={{ position: 'absolute', bottom: 'calc(100% + 8px)', ... }} />
    </VoteFeedback.Root>
  </div>
}
```

### Abandon signal in App

`useEffect` registers a `beforeunload` handler that fires a `user-abandon` EVENT signal when the user closes or navigates away mid-session:

```tsx
useEffect(() => {
  const handleUnload = () => {
    if (sessionId && messages.length > 0) {
      sendSignal({ session_id: sessionId, kind: 'EVENT', source: 'HUMAN', trigger_name: 'user-abandon', score: 0.0 })
    }
  }
  window.addEventListener('beforeunload', handleUnload)
  return () => window.removeEventListener('beforeunload', handleUnload)
}, [sessionId, messages.length, sendSignal])
```

---

## Session ID Flow

The session ID travels through the full stack:

```
POST /api/chat  →  X-Session-ID response header
        ↓
React state: setSessionId(sid)   [captured from headers on every response]
        ↓
VoteFeedback.Root session_id={sessionId}
        ↓
useKeletSignal() calls: { session_id: sessionId, ... }
```

- `sessionId` starts as `''` and is set on the first response
- VoteFeedback and signal hooks only fire when `sessionId` is non-empty (guarded with `{sessionId && ...}`)
- The same `sessionId` is passed back as `session_id` in subsequent `POST /api/chat` body, ensuring continuity

---

## Styling

All new UI elements use the app's existing CSS classes from `App.module.css`:
- `styles.iconBtn` — for thumbs up/down and copy buttons
- `styles.sendBtn` — for the feedback popover submit button
- `styles.assistantMessage` — wraps the message + feedback row

Popover inline styles follow the app's dark color palette (`#1e2130` background, `#2d3748` borders, `#e2e8f0` text, `#0f1117` textarea background) to match the existing chat UI.

---

## Verification Notes

- No nested `<button>` elements: `VoteFeedback.UpvoteButton` and `VoteFeedback.DownvoteButton` use `asChild` to merge onto the app's `<button>` — valid HTML
- Popover positioning: parent `div` has `position: relative`; `VoteFeedback.Popover` has `position: absolute; bottom: calc(100% + 8px)` — floats above buttons
- Secret key (`KELET_API_KEY`) is in root `.env` only — never in the Vite bundle
- Publishable key is in `frontend/.env` and read via `import.meta.env.VITE_KELET_PUBLISHABLE_KEY`
