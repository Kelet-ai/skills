# Frontend Changes

## Files Modified

### `frontend/src/main.tsx`
Added `KeletProvider` wrapping `<App />` at the React root. Uses:
- `apiKey={import.meta.env.VITE_KELET_PUBLISHABLE_KEY}` — publishable key from Vite env (NOT the secret key)
- `project={import.meta.env.VITE_KELET_PROJECT}` — project name from env var

### `frontend/src/App.tsx`
Refactored to extract an `AssistantMessage` component. Added `VoteFeedback` compound component on each assistant message bubble.

### `frontend/src/App.module.css`
Created with app theme (dark backgrounds, blue accents). Includes `.iconBtn` class already defined.

---

## VoteFeedback Styling — How Buttons Match the App Theme

The app uses CSS modules with a dark theme:
- Background: `#0f1117` (page) / `#1e2130` (cards/messages)
- Blue accent: `#3b82f6`
- Muted icon color: `#64748b` → `#e2e8f0` on hover
- Button style for icon-like actions: `.iconBtn` in `App.module.css`

### Vote buttons (`UpvoteButton` / `DownvoteButton`)

Used `asChild` prop (Radix-style) so the vote buttons render as the app's own `<button className={styles.iconBtn}>` element. This pattern merges the VoteFeedback click handlers onto the child element via `cloneElement` — avoiding nested `<button>` elements (which would be invalid HTML and silently corrupt HMR).

```tsx
<VoteFeedback.UpvoteButton asChild>
  <button className={styles.iconBtn} aria-label="Helpful">▲</button>
</VoteFeedback.UpvoteButton>
<VoteFeedback.DownvoteButton asChild>
  <button className={styles.iconBtn} aria-label="Not helpful">▼</button>
</VoteFeedback.DownvoteButton>
```

`.iconBtn` CSS:
```css
.iconBtn { background: transparent; border: none; color: #64748b; cursor: pointer; padding: 0.25rem; border-radius: 0.25rem; font-size: 0.875rem; }
.iconBtn:hover { color: #e2e8f0; background: #2d3748; }
```

Result: subtle, muted icon-style buttons that become bright on hover — consistent with the dark theme's visual language. No emoji, no arbitrary inline styles.

### Popover

Styled inline to match the dark theme:
- `background: #1e2130` (matches assistant message bubble background)
- `border: 1px solid #2d3748` (matches input border color)
- `borderRadius: 0.5rem`

### Textarea inside Popover

Styled inline:
- `background: #0f1117` (deep background)
- `color: #e2e8f0`
- `border: 1px solid #2d3748`

### Submit button

Uses `className={styles.sendBtn}` — the same CSS module class as the main Send button, providing visual consistency (blue `#3b82f6` fill, white text, rounded corners).

---

## Session ID Propagation

The session ID travels end-to-end:
1. Server generates UUID on first request → stores in Redis session
2. Server returns it in `X-Session-ID` response header (`expose_headers` already configured in CORS middleware)
3. React state: `setSessionId(res.headers.get('X-Session-ID'))`
4. `VoteFeedback.Root session_id={sessionId}` — uses the exact same value the server used in `agentic_session(session_id=session.session_id)`

This ensures feedback signals are linked to the correct trace in Kelet.

---

## What Was NOT Changed

- `app/main.py` — `kelet.configure()` was already present
- `src/routers/chat.py` — `kelet.agentic_session()` was already wrapping the agent stream
- `pyproject.toml` — `kelet>=1.3.0` already in dependencies
- `.env` — `KELET_API_KEY` + `KELET_PROJECT` + `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT` already set
