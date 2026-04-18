# Frontend Changes

## Where VoteFeedback Was Placed

VoteFeedback.Root is rendered inside a new `AssistantMessage` component in `frontend/src/App.tsx`, immediately after the message content span. It is conditionally rendered: only when `sessionId` is non-empty (meaning at least one round-trip has completed and a session ID has been captured from X-Session-ID).

Location in the component tree:

```
<div className={styles.chat}>
  <div className={styles.messages}>
    {messages.map((m, i) => (
      m.role === 'user'
        ? <div key={i} className={styles.userMessage}>...</div>
        : <AssistantMessage key={i} content={m.content} sessionId={sessionId} />
    ))}
  </div>
  ...
</div>
```

Inside `AssistantMessage`:

```
<div className={styles.assistantMessage}>
  <span className={styles.messageContent}>{content}</span>
  {sessionId && (
    <div style={{ position: 'relative', display: 'inline-flex', ... }}>
      <VoteFeedback.Root session_id={sessionId}>
        <VoteFeedback.UpvoteButton asChild>
          <button className={styles.iconBtn} aria-label="Helpful">▲</button>
        </VoteFeedback.UpvoteButton>
        <VoteFeedback.DownvoteButton asChild>
          <button className={styles.iconBtn} aria-label="Not helpful">▼</button>
        </VoteFeedback.DownvoteButton>
        <VoteFeedback.Popover style={{ position: 'absolute', bottom: 'calc(100% + 8px)', ... }}>
          <VoteFeedback.Textarea ... />
          <VoteFeedback.SubmitButton className={styles.sendBtn}>Submit</VoteFeedback.SubmitButton>
        </VoteFeedback.Popover>
      </VoteFeedback.Root>
      <button className={styles.iconBtn} onClick={handleCopy}>
        {copied ? '✓' : '⎘'}
      </button>
    </div>
  )}
</div>
```

## How Session ID Flows

1. React state: `const [sessionId, setSessionId] = useState<string>('')`
2. On each `/api/chat` response: `const sid = res.headers.get('X-Session-ID'); if (sid) setSessionId(sid)`
3. Passed to AssistantMessage as prop: `<AssistantMessage sessionId={sessionId} ... />`
4. Passed to VoteFeedback: `<VoteFeedback.Root session_id={sessionId}>`
5. Backend: `agentic_session(session_id=session.session_id)` — same UUID used in both places

The session ID is server-generated and returned via `X-Session-ID` response header. The `expose_headers: ['X-Session-ID']` CORS configuration was already present in main.py — required for the browser to read this header from cross-origin requests.

## VoteFeedback Popover Positioning

The Popover is given `position: absolute; bottom: calc(100% + 8px)` to float above the buttons, as required by the API reference (VoteFeedback.Popover renders as a plain `role="dialog"` div with NO built-in positioning). The parent `<div>` wrapping VoteFeedback.Root has `position: relative` to serve as the CSS positioning context.

The existing App.css uses no `overflow: hidden` on message containers, so Popover clipping is not a risk.

## Theme/Style Considerations

The existing App.tsx uses CSS Modules (`styles.*`). VoteFeedback buttons use `asChild` with the existing `styles.iconBtn` class to match the existing button style. The Popover uses inline styles matching the existing dark UI palette (`#1e2130` background, `#2d3748` border, matching the chat's color scheme). The SubmitButton reuses `styles.sendBtn` — the same class used by the Send button in the input row.

No new CSS classes were introduced — the integration matches the existing styling approach.

## Implicit Signals Beyond VoteFeedback

Two additional coded signals were added:

### 1. Copy-to-clipboard signal (`user-copy`)
```tsx
const handleCopy = async () => {
  await navigator.clipboard.writeText(content)
  sendSignal({ session_id: sessionId, kind: 'EVENT', source: 'HUMAN', trigger_name: 'user-copy' })
}
```
A copy event means the user found the answer valuable enough to extract — a positive implicit signal. Contrasted against downvotes, it helps Kelet distinguish "good answer I want to save" from "answer I need to complain about."

### 2. Session abandon signal (`user-abandon`)
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
A tab/window close after interaction means the user left without getting what they needed — a strong implicit dissatisfaction signal. `score: 0.0` marks it as negative.

## KeletProvider Placement

KeletProvider wraps the entire app in `frontend/src/main.tsx`, reading from Vite env vars:
- `VITE_KELET_PUBLISHABLE_KEY` → `apiKey` prop (publishable key, safe for frontend bundle)
- `VITE_KELET_PROJECT` → `project` prop

The publishable key (`kelet_pk_...`) is used here, never the secret key (`kelet_sk_...`). The secret key is server-only and only written to `.env` for the Python backend.

## Common Mistakes Avoided

- `VoteFeedback.UpvoteButton` and `VoteFeedback.DownvoteButton` use `asChild` to merge handlers onto custom `<button>` elements — avoids invalid nested buttons that silently corrupt HMR
- Popover has `position: absolute` and parent has `position: relative` — avoids invisible-popover failure mode
- `session_id` passed to `VoteFeedback.Root` is the exact same value used in `agentic_session()` on the server — ensures feedback is linked to traces
- Publishable key in KeletProvider, secret key in Python configure() — keys never mixed
