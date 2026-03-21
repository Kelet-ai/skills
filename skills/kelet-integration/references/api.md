# Kelet SDK API Reference

## Package Names

| Stack | Package |
|---|---|
| Python | `kelet` (pip/uv) |
| TypeScript / Node.js | `kelet` (npm) |
| React frontend | `@kelet-ai/feedback-ui` (npm) |
| Python extras | `kelet[anthropic]`, `kelet[openai]`, `kelet[langchain]`, `kelet[all]` |

## Python SDK

Functions (all in `kelet` namespace):
- `kelet.configure(*, api_key=None, project=None, base_url=None)` — call once at startup
- `kelet.agentic_session(*, session_id, user_id=None, project=None)` — async/sync context manager AND decorator
- `kelet.agent(*, name)` — context manager; names an agent within a session for readable multi-agent traces
- `async kelet.signal(kind, source, *, session_id=None, ...)` — submit a signal; auto-resolves session from context
- `kelet.get_session_id()` — get current session ID from context
- `kelet.create_kelet_processor()` — for manual OTEL setup (e.g. `logfire.configure(additional_span_processors=[kelet.create_kelet_processor()])`)

## TypeScript SDK

**Critical difference from Python**: `agenticSession` is **callback-based**, not a context manager.

```
agenticSession({ sessionId, userId? }, async () => { ... })  // returns callback's return value
```

Uses `AsyncLocalStorage` — Node.js only, not browser-compatible.

Other functions:
- `configure({ apiKey, project, apiUrl })` — call once at startup
- `signal({ kind, source, sessionId?, traceId?, ... })` — returns Promise<void>
- `getSessionId()`, `getUserId()`, `getTraceId()` — read from current context

## Next.js

Use `KeletExporter` in `instrumentation.ts` via `@vercel/otel`:
- `new KeletExporter({ apiKey, project })`

## React (`@kelet-ai/feedback-ui`)

- `KeletProvider({ apiKey?, project, baseUrl? })` — `apiKey` optional if a parent provider already set it
- `VoteFeedback.Root({ session_id, onFeedback? })` — compound component root
- `VoteFeedback.UpvoteButton`, `VoteFeedback.DownvoteButton`, `VoteFeedback.Popover`, `VoteFeedback.Textarea`, `VoteFeedback.SubmitButton`
- `useFeedbackState<T>(initialState, session_id, options?)` — drop-in for `useState`; tracks edits automatically

## Env Vars

| Variable | Where | What |
|---|---|---|
| `KELET_API_KEY` | Server | Secret key — required; configure() raises ValueError if missing |
| `KELET_PROJECT` | Server (optional) | Default project name |
| `KELET_API_URL` | Server (optional) | Custom endpoint (self-hosted) |
| `VITE_KELET_PUBLISHABLE_KEY` | Vite frontend | Publishable key for KeletProvider |
| `NEXT_PUBLIC_KELET_PUBLISHABLE_KEY` | Next.js | Same, Next.js convention |
