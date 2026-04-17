# Frontend Changes

## Overview

The frontend is a new Vite + React app (not previously tracked in git on the `without-kelet` branch). All frontend files are new additions. The app has a minimal dark-theme chat UI.

---

## Files Created / Modified

### `frontend/package.json` (new)
Added `@kelet-ai/feedback-ui` as a dependency alongside React 18 and Vite 5. No changes to devDependencies required — React and TypeScript were already planned.

### `frontend/src/main.tsx` (new)
**KeletProvider** wraps the entire app at the root. This is required before any `VoteFeedback`, `useFeedbackState`, or `useKeletSignal` hook can be used anywhere in the tree.

```tsx
<KeletProvider
  apiKey={import.meta.env.VITE_KELET_PUBLISHABLE_KEY}
  project={import.meta.env.VITE_KELET_PROJECT}
>
  <App />
</KeletProvider>
```

Key decisions:
- Uses `VITE_KELET_PUBLISHABLE_KEY` (publishable `pk-kelet-...` key) — NOT the secret key. The publishable key is safe to ship in a frontend bundle.
- `project` read from `VITE_KELET_PROJECT` env var — never hardcoded.

### `frontend/src/App.tsx` (new)
Two Kelet additions relative to a plain chat UI:

#### 1. `VoteFeedback` component (explicit thumbs up/down)
Added to every `AssistantMessage`. The component structure follows the safe pattern:
- `VoteFeedback.Root` wraps with `session_id={sessionId}`.
- `VoteFeedback.UpvoteButton asChild` / `VoteFeedback.DownvoteButton asChild` — uses the `asChild` pattern to merge Kelet's click handlers onto the app's own `<button className={styles.iconBtn}>` elements. This avoids the nested-button anti-pattern that silently corrupts HMR.
- `VoteFeedback.Popover` positioned absolutely: `bottom: calc(100% + 8px)`, `left: 0`, `zIndex: 10`. The parent container has `position: relative` (via inline style on the wrapping div). No `overflow: hidden` on any ancestor — popover will render correctly.
- `VoteFeedback.Textarea` and `VoteFeedback.SubmitButton` inside the popover — styled with the app's dark palette (`background: #1e2130`, `color: #e2e8f0`, `border: 1px solid #2d3748`) to match `App.module.css`.

#### 2. Copy button with `useKeletSignal` (implicit copy signal)
A copy-to-clipboard button added to each assistant message, using the `useKeletSignal` hook:
```tsx
const sendSignal = useKeletSignal()
const handleCopy = () => {
  navigator.clipboard.writeText(content)
  if (sessionId) {
    sendSignal({ session_id: sessionId, kind: 'EVENT', source: 'HUMAN', trigger_name: 'user-copy' })
  }
}
```
- Styled with `styles.iconBtn` — same ghost-button class as the vote buttons.
- Sends an `EVENT / HUMAN` signal with `trigger_name: 'user-copy'`. When a user copies the AI output, it's a strong implicit positive signal — the user found the answer useful enough to take with them.
- The button is rendered OUTSIDE `VoteFeedback.Root` to avoid any nested-button concern.

### `frontend/src/App.module.css` (new)
No changes to the CSS — existing classes (`iconBtn`, `sendBtn`, `assistantMessage`, etc.) were used as-is for all new UI elements. The VoteFeedback popover uses inline styles that match the design tokens from the module CSS (same color palette: `#0f1117`, `#1e2130`, `#2d3748`, `#e2e8f0`).

### `frontend/.env` (new)
```
VITE_KELET_PUBLISHABLE_KEY=pk-kelet-...
VITE_KELET_PROJECT=docs-ai-assistant
```
Should be added to `.gitignore` (the root `.gitignore` already covers `*.env` patterns — confirm).

---

## Session ID Propagation

Session ID flows end-to-end:

1. **Initial request**: React sends `POST /api/chat` with `session_id: ""` (empty string initial state).
2. **Server auto-creates** session UUID via `create_session()`, runs `agentic_session(session_id=session.session_id)`, returns `X-Session-ID` response header.
3. **React stores** the session ID: `const sid = res.headers.get('X-Session-ID'); if (sid) setSessionId(sid)`.
4. **Subsequent requests** send `session_id: sessionId` in the request body — server looks up existing session, continues conversation history.
5. **VoteFeedback** receives `session_id={sessionId}` — this matches exactly what the server used in `agentic_session()`, so votes are correctly linked to traces in the Kelet console.
6. **Copy signal** also uses `session_id={sessionId}` — linked to the same session.

The `X-Session-ID` header is already listed in the CORS `expose_headers` on the backend, so the browser can read it cross-origin.

---

## Styling Decisions

All new UI elements use existing CSS module classes and the app's established color palette:
- Ghost buttons for copy/vote: `styles.iconBtn` (`color: #64748b`, hover: `#e2e8f0` on `#2d3748`)
- Primary action button: `styles.sendBtn` (`background: #3b82f6`, `color: white`)
- Dark popover: matches `assistantMessage` background (`#1e2130`) with `#2d3748` borders
- Text color: `#e2e8f0` throughout

No new CSS classes added. No emoji defaults used (text/symbol characters used for button icons to match the existing `▲`/`▼` style in the reference implementation).

---

## What Is NOT Changed

- No `useFeedbackState` — there are no editable AI output fields in this UI. The AI response renders as a read-only `<span>`. Edit tracking requires an `<input>` or `<textarea>` where the user modifies the AI output. This chat UI doesn't have that pattern.
- No additional backend signals beyond the existing `agent-stream-error` signal that was added in `chat.py`.
