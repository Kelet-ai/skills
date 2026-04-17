# Frontend Changes

## Where VoteFeedback Was Placed

VoteFeedback.Root is rendered inside each assistant message div in `frontend/src/App.tsx`, immediately after the `<span>{m.content}</span>`. It is conditionally rendered: only when `m.role === 'assistant'` AND `sessionId` is non-empty (meaning at least one round-trip has completed and a session ID has been captured from X-Session-ID).

Location in the component tree:
```
<div className="chat">
  <div className="messages">
    {messages.map((m, i) => (
      <div key={i} className={`message ${m.role}`}>
        <span>{m.content}</span>
        {m.role === 'assistant' && sessionId && (
          <div style={{ position: 'relative', display: 'inline-block', marginTop: 4 }}>
            <VoteFeedback.Root session_id={sessionId}>
              ...
            </VoteFeedback.Root>
          </div>
        )}
      </div>
    ))}
  </div>
  ...
</div>
```

## How Session ID Flows

1. React state: `const [sessionId, setSessionId] = useState<string>('')`
2. On each `/api/chat` response: `const sid = res.headers.get('X-Session-ID'); if (sid) setSessionId(sid)`
3. Passed to VoteFeedback: `<VoteFeedback.Root session_id={sessionId}>`
4. Backend: `agentic_session(session_id=session.session_id)` — same UUID used in both places

The session ID is server-generated and returned via `X-Session-ID` response header. The `expose_headers: ['X-Session-ID']` CORS configuration was already present in main.py, which is required for the browser to read this header from cross-origin requests.

## VoteFeedback Popover Positioning

The Popover is given `position: absolute; bottom: calc(100% + 8px)` to float above the buttons, as required by the API reference (VoteFeedback.Popover renders as a plain div with NO built-in positioning). The parent `<div>` wrapping VoteFeedback.Root has `position: relative` to serve as the CSS positioning context.

The App uses className-based styling (`className="chat"`, `className="message assistant"`) with no global overflow:hidden on message containers, so Popover clipping is not a risk.

## Theme/Style Considerations

The original App.tsx used inline styles for a minimal chat UI. The VoteFeedback buttons (UpvoteButton, DownvoteButton) render with plain SVG/emoji content matching the plain style of the existing chat. The Popover uses inline styles matching the existing UI palette (white background, `#ccc` border, `border-radius: 8px`, and blue `#0070f3` for the submit button — same blue used in the Send button).

No CSS classes were added — the integration fits the existing inline-style approach without introducing any style system dependency.

## KeletProvider Placement

KeletProvider wraps the entire app in `frontend/src/main.tsx`, reading from Vite env vars:
- `VITE_KELET_PUBLISHABLE_KEY` → `apiKey` prop (publishable key, safe for frontend bundle)
- `VITE_KELET_PROJECT` → `project` prop

The publishable key (`pk-kelet-...`) is used, never the secret key (`sk-kelet-...`). The secret key is server-only and only written to `.env` for the Python backend.

## Common Mistakes Avoided

- VoteFeedback.UpvoteButton and DownvoteButton use direct children (span/emoji), never wrapping content in another <button> — avoids nested buttons that silently corrupt HMR
- Popover has position:absolute and parent has position:relative — avoids invisible-popover failure mode
- session_id passed to VoteFeedback.Root is the exact same value used in agentic_session() on the server — ensures feedback is linked to traces
- Publishable key in KeletProvider, secret key in Python configure() — keys not mixed
