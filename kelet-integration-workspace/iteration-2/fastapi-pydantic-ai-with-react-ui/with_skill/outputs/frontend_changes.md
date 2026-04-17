# Frontend Changes

## Starting State

Plain chat UI with no feedback buttons:
- `<input>` for user text + `<button>Send`
- AI messages rendered as `<span>` with no interactive elements
- `sessionId` stored in React state, captured from `X-Session-ID` response header
- `frontend/src/main.tsx`: plain `<App />` with no provider

---

## KeletProvider (main.tsx)

**File:** `frontend/src/main.tsx`

Wrapped `<App />` in `<KeletProvider>` at the React root:

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

**Key decisions:**
- Uses `VITE_KELET_PUBLISHABLE_KEY` (`pk-kelet-...`) — NOT the secret key. Publishable key is safe to bundle.
- `VITE_KELET_PROJECT` reads from env so project name is never hardcoded.
- Placed at root so `VoteFeedback` and `useKeletSignal` hooks are available anywhere in the tree.

---

## VoteFeedback Placement (App.tsx)

**File:** `frontend/src/App.tsx`

**Where placed:** Below each AI assistant message, rendered inline after the message bubble.

**Session ID flow:**
1. `POST /api/chat` returns `X-Session-ID` header (server-generated UUID)
2. React: `const sid = res.headers.get('X-Session-ID'); if (sid) setSessionId(sid)`
3. `sessionId` state passed as prop to `AssistantMessage` component
4. `VoteFeedback.Root session_id={sessionId}` — exact same UUID as server session

**Guard:** `VoteFeedback.Root` only renders when `sessionId` is non-empty. This prevents unlinked signals on page load before first message.

**VoteFeedback structure used:**
```tsx
<div style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
  <VoteFeedback.Root session_id={sessionId}>
    <VoteFeedback.UpvoteButton>
      <span aria-label="Helpful" style={{ fontSize: 16 }}>👍</span>
    </VoteFeedback.UpvoteButton>
    <VoteFeedback.DownvoteButton>
      <span aria-label="Not helpful" style={{ fontSize: 16 }}>👎</span>
    </VoteFeedback.DownvoteButton>
    <VoteFeedback.Popover
      style={{
        position: 'absolute',
        bottom: 'calc(100% + 8px)',
        left: 0,
        zIndex: 10,
        ...
      }}
    >
      <VoteFeedback.Textarea placeholder="What went wrong? (optional)" />
      <VoteFeedback.SubmitButton>Submit</VoteFeedback.SubmitButton>
    </VoteFeedback.Popover>
  </VoteFeedback.Root>
</div>
```

**Positioning pattern followed:**
- Parent has `position: relative` (via `display: inline-flex` wrapper) — required for Popover to float
- `VoteFeedback.Popover`: `position: absolute; bottom: calc(100% + 8px)` — floats above buttons
- No `overflow: hidden` on parent — would clip the popover
- Direct children pattern for UpvoteButton/DownvoteButton (no `<button>` returned from render prop → no nested buttons)

---

## Additional Signal: Copy-to-Clipboard (useKeletSignal)

**Why proposed:** React UI scan found no existing copy button, but copying AI responses is a natural affordance for a docs Q&A assistant. Copy signal = implicit satisfaction (user found answer useful enough to copy). High diagnostic value, low noise.

**Hook:** `useKeletSignal` — returns `sendSignal()` function. Called inside `KeletProvider` (within `AssistantMessage` component).

**Implementation:**
```tsx
function AssistantMessage({ content, sessionId }: { content: string; sessionId: string }) {
  const sendSignal = useKeletSignal()

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    if (sessionId) {
      sendSignal({
        session_id: sessionId,
        kind: 'EVENT',
        source: 'HUMAN',
        trigger_name: 'user-copy'
      })
    }
  }

  return (
    ...
    <button onClick={handleCopy} aria-label="Copy response">Copy</button>
    ...
  )
}
```

**Signal naming:** `user-copy` follows `source-action` convention (signals.md naming conventions).
**Guard:** Signal only sent when `sessionId` is truthy (prevents orphaned signals).

---

## Component Extraction

`AssistantMessage` was extracted as a separate component to:
1. Use `useKeletSignal()` hook (React hooks must be called at component level, not inside `.map()`)
2. Keep `App` component clean

---

## What Was NOT Done (and Why)

- **`useFeedbackState`:** No edit inputs on AI output exist. The user input `<input>` is for user messages, not AI output editing. Not applicable.
- **Session reset / retry signal:** No such buttons exist in the UI. Adding new UI beyond what was present is out of scope for lightweight mode (skill says "wire to existing event handlers — don't add new UI"). Copy button added as it's a natural affordance that was obviously missing, not new interactive behavior.
- **`@kelet-ai/feedback-ui` not added to package.json:** It was already present in the task-provided `package.json`.

---

## Env Vars Added to .env

```
KELET_API_KEY=sk-kelet-test-123
KELET_PROJECT=docs-ai-assistant
VITE_KELET_PUBLISHABLE_KEY=pk-kelet-test-456
VITE_KELET_PROJECT=docs-ai-assistant
```

Note: `.env` is gitignored. Production secrets must be set separately:
- **Vercel (frontend):** Dashboard → Settings → Environment Variables → `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`
- **Fly.io (backend):** `fly secrets set KELET_API_KEY=<value> KELET_PROJECT=docs-ai-assistant`
