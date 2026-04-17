# Skill Execution Transcript — Expand to Full Mode

**Task prompt:** "I want to go deeper with Kelet — add more signals and get better coverage"
**App:** FastAPI + pydantic-ai docs Q&A assistant. Plain HTML frontend (Vite + React, no component library).

---

## What Was Already Done

The developer's codebase already had a solid lightweight integration in place:

1. **`kelet.configure()`** called once at startup in `app/main.py` — reads `KELET_API_KEY` and `KELET_PROJECT` from environment. Correct.
2. **`kelet.agentic_session(session_id=session.session_id)`** wrapping the streaming generator in `src/routers/chat.py`. Correct placement.
3. **`VoteFeedback.Root / UpvoteButton / DownvoteButton / Popover / Textarea / SubmitButton`** in `frontend/src/App.tsx`, using `asChild` correctly on the buttons to avoid nested-button pitfall. Positioned correctly with `position: relative` wrapper and `position: absolute` on the Popover.
4. **`agent-stream-error` signal** in the exception handler — catches streaming failures and marks score 0.0.
5. **`X-Session-ID` header** exposed via `expose_headers` in CORS middleware and captured by the frontend from `res.headers.get('X-Session-ID')` — ensuring VoteFeedback session linkage is correct.
6. **`@kelet-ai/feedback-ui`** already in `frontend/package.json`.

The integration was already correct and complete for lightweight mode. No setup or structural changes needed.

---

## Signal Analysis (Internal Reasoning)

### What the app does
Multi-turn documentation Q&A. User asks questions about product docs; the pydantic-ai agent uses BM25 search (`search_docs` tool) and page retrieval (`get_page` tool) to answer. Sessions are maintained via Redis with UUID session IDs. Conversation history is persisted per session.

### Existing signal coverage
- Vote (up/down) — FEEDBACK / HUMAN via VoteFeedback
- Stream error — EVENT / LABEL (server-side, automated)

### Gap analysis for full mode

**Copy signal** — The app renders AI text as plain text (`{content}` in a `<span>`). Docs answers are frequently copy-pasted by developers reading documentation. Copy = strong implicit satisfaction signal. A copy button is a natural affordance for this use case, and hooking it gives Kelet a "found it useful enough to copy" signal. Uses `useKeletSignal`. Trigger name: `user-copy`.

**New conversation / abandon signal** — The current frontend has no way to start a fresh conversation. When a user sends a new message to an existing session, it continues. There's no "new chat" button. Adding one serves both UX (clear conversation) and signal coverage: clicking "New Chat" is an implicit abandonment of the previous session. Uses `useKeletSignal` with score 0.0 and trigger `user-abandon`. The session reset clears `sessionId` state, which will cause the next request to create a new server session.

**RAG faithfulness / hallucination** — The agent uses retrieval tools, making RAG Faithfulness a strong synthetic candidate. However, this was deprioritized in favor of platform-managed synthetics (Kelet can see the tool call outputs in the trace and evaluate faithfulness without any code). No coded signal needed.

**Tool call failure / rate limit** — Already surfaced structurally: HTTP 429 raises before reaching the agent. The stream error signal catches agent-level failures. No additional server-side coded signal needed beyond what's already there.

### Synthetic evaluators selected (full mode)

| Evaluator | Category | Rationale |
|---|---|---|
| `Task Completion` | Usefulness | Primary anchor — did the agent answer the doc question? |
| `Conversation Completeness` | Comprehension | Doc assistants often deflect off-topic or leave multi-part questions partially answered |
| `Knowledge Retention` | Behavior | Multi-turn: agent must remember what docs user already found, what their use case is |
| `Sentiment Analysis` | User reaction | Detects repeated frustration — user asking the same question differently = agent failed |

Excluded: `RAG Faithfulness` (valuable but overlaps Task Completion for this app — adds noise without distinct category), `Answer Relevancy` (covered by Task Completion for single-intent queries), `Session Health Stats` (structural data already visible in trace). Kept to 4 evaluators, one per distinct failure category.

---

## What Was Added

### 1. Copy-to-clipboard signal (`user-copy`)

**Where:** `frontend/src/App.tsx`, inside `AssistantMessage` component.

**Why:** Copy is the highest-value implicit satisfaction signal for a documentation assistant. The user copying an answer means it was useful and specific enough to act on. Kelet can correlate copy events to the session trace to identify which answer types get copied vs. ignored. Low noise (intentional action), high signal strength.

**How:** Added a copy `<button>` to `AssistantMessage` using the existing `.iconBtn` CSS class. On click, it writes `content` to clipboard and calls `useKeletSignal` → `sendSignal({ session_id: sessionId, kind: 'EVENT', source: 'HUMAN', trigger_name: 'user-copy', score: 1.0 })`. Score 1.0 = user found this answer useful enough to copy.

**Key detail:** `useKeletSignal` must be called inside a `KeletProvider`. Added `KeletProvider` wrapping at the App root with `VITE_KELET_PUBLISHABLE_KEY` (publishable key, frontend-safe) and `VITE_KELET_PROJECT` env vars. The existing VoteFeedback was already using `@kelet-ai/feedback-ui` but `KeletProvider` was not yet present — this is required for `useKeletSignal`.

### 2. New conversation / abandon signal (`user-abandon`)

**Where:** `frontend/src/App.tsx`, new "New Chat" button in the input row.

**Why:** Starting a new conversation is the strongest implicit abandonment signal in a chat UI. The user giving up on a thread and resetting = the previous session did not meet their need. Kelet tags this against the session being abandoned, enabling RCA to identify sessions that end in resets.

**How:** Added a "New Chat" button styled with `.iconBtn` class (matches existing palette). On click: sends `user-abandon` signal with score 0.0 against the current `sessionId` (if any), then clears `messages`, `input`, and `sessionId` state. Clearing `sessionId` means the next POST `/chat` will create a new server-side session.

**Signal timing:** Signal is sent before state reset so `sessionId` is still available for attribution.

### 3. `KeletProvider` wrapper

Required for `useKeletSignal` to work. Added around the `<App>` root in `frontend/src/main.tsx`. Uses `VITE_KELET_PUBLISHABLE_KEY` (publishable key) and `VITE_KELET_PROJECT` env vars — both frontend-safe, never the secret `KELET_API_KEY`.

### 4. Synthetic evaluators deeplink

**Deeplink URL:**
`https://console.kelet.ai/docs_ai/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBcdTIwMTQgdXNlcnMgYXNrIHF1ZXN0aW9ucyBhYm91dCBwcm9kdWN0IGRvY3MsIGFnZW50IHNlYXJjaGVzIGFuZCByZXRyaWV2ZXMgcGFnZXMsIGFuc3dlcnMgaW4gbXVsdGktdHVybiBjb252ZXJzYXRpb24iLCJpZGVhcyI6W3sibmFtZSI6IlRhc2sgQ29tcGxldGlvbiIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJEaWQgdGhlIGFnZW50IHN1Y2Nlc3NmdWxseSBhbnN3ZXIgdGhlIHVzZXIgcXVlc3Rpb24gd2l0aCByZWxldmFudCBkb2N1bWVudGF0aW9uIGNvbnRlbnQ_In0seyJuYW1lIjoiQ29udmVyc2F0aW9uIENvbXBsZXRlbmVzcyIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJXZXJlIGFsbCB1c2VyIHF1ZXN0aW9ucyBhZGRyZXNzZWQsIG9yIGRpZCB0aGUgYWdlbnQgZGVmbGVjdCBvciBsZWF2ZSBxdWVzdGlvbnMgdW5hbnN3ZXJlZD8ifSx7Im5hbWUiOiJLbm93bGVkZ2UgUmV0ZW50aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgcmVtZW1iZXIgYW5kIGNvcnJlY3RseSB1c2UgY29udGV4dCBmcm9tIGVhcmxpZXIgdHVybnMgaW4gdGhlIGNvbnZlcnNhdGlvbj8ifSx7Im5hbWUiOiJTZW50aW1lbnQgQW5hbHlzaXMiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiRGV0ZWN0IHVzZXIgZnJ1c3RyYXRpb24sIHJlcGVhdGVkIGNvcnJlY3Rpb25zLCBvciBkaXNzYXRpc2ZhY3Rpb24gc2lnbmFscyBhY3Jvc3MgdGhlIHNlc3Npb24ifV19`

Activate this link in the Kelet console to configure all 4 evaluators. No code needed — they run on the platform against existing trace data.

---

## Environment Variables Added

| Variable | File | Notes |
|---|---|---|
| `VITE_KELET_PUBLISHABLE_KEY` | `frontend/.env` | Publishable key (`pk-kelet-...`) — frontend-safe |
| `VITE_KELET_PROJECT` | `frontend/.env` | Project name for KeletProvider |

Both added to `.gitignore`. The backend already has `KELET_API_KEY` and `KELET_PROJECT` wired via `kelet.configure()`.

---

## What You'll See in the Kelet Console

| After this change | Visible in Kelet console |
|---|---|
| VoteFeedback (already present) | Signals: thumbs up/down correlated to exact trace |
| Copy signal | Signals: `user-copy` events — which answers users found useful enough to copy |
| Abandon signal | Signals: `user-abandon` — sessions that ended in a fresh start |
| Platform synthetics | Signals: Task Completion, Conversation Completeness, Knowledge Retention, Sentiment Analysis scores per session — automated, no further code |

---

## Verification Checklist

- `KeletProvider` at root — `VITE_KELET_PUBLISHABLE_KEY` (publishable) not secret key
- `useKeletSignal` called inside `KeletProvider` tree
- `user-abandon` signal fires before `setSessionId('')` so the session ID is still available
- `user-copy` sends score 1.0 (explicit positive)
- `user-abandon` sends score 0.0 (explicit negative)
- `VoteFeedback.Root` `session_id` still matches `X-Session-ID` header value after this refactor
- After frontend changes: verify existing vote buttons still render correctly
