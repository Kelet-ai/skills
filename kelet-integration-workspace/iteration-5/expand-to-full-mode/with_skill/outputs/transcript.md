# Eval Transcript — Expand to Full Mode

**Prompt**: "I want to go deeper with Kelet — add more signals and get better coverage"
**App**: FastAPI + pydantic-ai docs Q&A assistant. Plain HTML/React frontend. Already has `kelet.configure()`, `agentic_session()`, `KeletProvider`, and `VoteFeedback` wired.

---

## What Was Already in Place

The `without-kelet` branch already had these Kelet integrations committed:

- `kelet.configure()` called at startup in `app/main.py`
- `kelet.agentic_session(session_id=session.session_id)` wrapping the entire SSE streaming generator in `src/routers/chat.py`
- `KeletProvider` at React root in `frontend/src/main.tsx`
- `VoteFeedback.Root` / `UpvoteButton` / `DownvoteButton` / `Popover` on every assistant message in `frontend/src/App.tsx`
- Session ID flow: server generates UUID → stored in Redis → returned in `X-Session-ID` response header → captured by frontend → threaded into `VoteFeedback.Root session_id` prop

**Gap**: no error signal, no tool-call signals, no implicit behavioral signals (copy, abandon, retry).

---

## What Was Added

### 1. `agent-stream-error` signal — `src/routers/chat.py`

**Why**: Any unhandled exception in the streaming generator is a failure event. Without a coded signal, Kelet sees a silent session end — no trace that something went wrong. Adding a `LABEL/EVENT` signal with `score=0.0` and `trigger_name="agent-stream-error"` marks the session as failed so RCA can cluster these cases.

**Signal**: `kind=EVENT`, `source=LABEL`, `trigger_name="agent-stream-error"`, `score=0.0`

---

### 2. `user-retry` signal — `src/routers/chat.py`

**Why**: When a user sends a second (or later) message on an existing session, it could mean they're continuing naturally OR they're rephrasing because the first answer was inadequate. Kelet can't distinguish without the signal — it sees multi-turn sessions but not whether those turns were continuations or corrections.

**How**: `_count_turns()` reads the stored session history JSON and counts completed model-role turns. If `>0`, the next incoming message is marked `is_retry=True`. Inside the `agentic_session` context, a `user-retry` signal fires with `score=0.0` (negative valence — retry = potential dissatisfaction).

**Signal**: `kind=EVENT`, `source=HUMAN`, `trigger_name="user-retry"`, `score=0.0`

**Rationale for server-side**: The app has no React router or page navigation — the "retry" concept lives at the API level where session history is available. No frontend hook needed.

---

### 3. `tool-search-docs` signal — `src/agent/__init__.py`

**Why**: The agent uses BM25 search as its primary retrieval path. A search that returns empty results (`found=False`) is a retrieval failure — either the docs don't cover the topic or the query formulation was poor. Kelet sees tool calls in traces but not whether retrieval succeeded. `score=0.0` on empty results enables RCA to correlate poor answers with retrieval gaps.

**How**: `search_docs` tool converted from `def` to `async def` (pydantic-ai supports both). After the BM25 call, fires a signal with the query and a boolean found flag in metadata.

**Signal**: `kind=EVENT`, `source=LABEL`, `trigger_name="tool-search-docs"`, `score=1.0|0.0`, `metadata={query, found}`

---

### 4. `tool-get-page` signal — `src/agent/__init__.py`

**Why**: `get_page` is the agent's second tool — fetch a specific doc page by slug. If the slug is wrong or the page doesn't exist, `get_page` returns a "not found" string and the agent may hallucinate or give up. Without a signal, a slug miss looks like a successful tool call in the trace. `score=0.0` on miss exposes retrieval failures.

**Signal**: `kind=EVENT`, `source=LABEL`, `trigger_name="tool-get-page"`, `score=1.0|0.0`, `metadata={slug, found}`

---

### 5. `user-copy` signal — `frontend/src/App.tsx`

**Why**: Copy-to-clipboard is a strong implicit positive signal — the user found the answer useful enough to use it. It's the clearest "good output" signal after an upvote, and it requires zero extra user action (they would copy anyway). Added `useKeletSignal` to `AssistantMessage` alongside the existing `VoteFeedback` buttons. The copy button reuses `styles.iconBtn` to match the app's existing icon button style.

**Signal**: `kind=EVENT`, `source=HUMAN`, `trigger_name="user-copy"` (no score — positive event)

---

### 6. `user-abandon` signal — `frontend/src/App.tsx`

**Why**: If a user closes the tab or navigates away mid-session after receiving responses, that's an implicit signal of dissatisfaction or task failure. The `beforeunload` event fires reliably before tab close. Guard: only fires if there's an active session and at least one message — prevents spurious fires on empty sessions.

**Signal**: `kind=EVENT`, `source=HUMAN`, `trigger_name="user-abandon"`, `score=0.0`

---

## Synthetic Evaluators Deeplink

Project: `docs-ai-assistant`

Evaluators selected (one per failure category, matched to actual agent behavior):

| Evaluator | Type | Category | Rationale |
|-----------|------|----------|-----------|
| Task Completion | llm | Usefulness | Anchor evaluator — did the agent answer the question? |
| RAG Faithfulness | llm | Correctness | Agent has BM25 + get_page retrieval; faithfulness checks answers stay within retrieved content |
| Answer Relevancy | llm | Comprehension | Docs Q&A agents commonly pad answers or miss the actual question |
| Conversation Completeness | llm | User reaction | Multi-turn sessions — were all user questions addressed across turns? |
| Loop Detection | code | Execution | Agent has two retrieval tools; repeated calls for same query/slug = retrieval loop |

**Deeplink**: `https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBcdTIwMTQgdXNlcnMgYXNrIHF1ZXN0aW9ucyBhYm91dCBrZWxldC5haSBkb2NzOyB0aGUgYWdlbnQgdXNlcyBCTTI1IHNlYXJjaCBhbmQgcGFnZSByZXRyaWV2YWwgdG9vbHMgdG8gYW5zd2VyLiBTZXNzaW9ucyBhcmUgbXVsdGktdHVybi4gS2V5IGZhaWx1cmUgbW9kZXM6IGhhbGx1Y2luYXRlZCBkb2MgY29udGVudCwgbWlzc2VkIHJldHJpZXZhbCwgaW5jb21wbGV0ZSBhbnN3ZXJzLCBvZmYtdG9waWMgcmVzcG9uc2VzLiIsImlkZWFzIjpbeyJuYW1lIjoiVGFzayBDb21wbGV0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgZnVsbHkgYW5zd2VyIHRoZSB1c2VyIHF1ZXN0aW9uIHVzaW5nIHRoZSBhdmFpbGFibGUgZG9jdW1lbnRhdGlvbj8ifSx7Im5hbWUiOiJSQUcgRmFpdGhmdWxuZXNzIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRvIHRoZSBhZ2VudCBjbGFpbXMgYWxpZ24gd2l0aCB0aGUgcmV0cmlldmVkIGRvY3VtZW50YXRpb24gcGFnZXM_IEZsYWcgYW5zd2VycyB0aGF0IGFkZCBjb250ZW50IG5vdCBwcmVzZW50IGluIHRoZSByZXRyaWV2ZWQgY29udGV4dC4ifSx7Im5hbWUiOiJBbnN3ZXIgUmVsZXZhbmN5IiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IklzIHRoZSByZXNwb25zZSBvbi10b3BpYyBhbmQgZGlyZWN0bHkgYWRkcmVzc2luZyB3aGF0IHRoZSB1c2VyIGFza2VkPyBGbGFnIHBhZGRpbmcsIHRhbmdlbnRzLCBvciBtaXNzZWQgcXVlc3Rpb25zLiJ9LHsibmFtZSI6IkNvbnZlcnNhdGlvbiBDb21wbGV0ZW5lc3MiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiV2VyZSBhbGwgdXNlciBpbnRlbnRpb25zIGFjcm9zcyB0aGUgc2Vzc2lvbiBhZGRyZXNzZWQsIG9yIGRpZCB0aGUgYWdlbnQgZGVmbGVjdCAvIGxlYXZlIHF1ZXN0aW9ucyB1bmFuc3dlcmVkPyJ9LHsibmFtZSI6Ikxvb3AgRGV0ZWN0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJjb2RlIiwiZGVzY3JpcHRpb24iOiJEZXRlY3QgcmVwZWF0ZWQgc2VhcmNoX2RvY3Mgb3IgZ2V0X3BhZ2UgY2FsbHMgZm9yIHRoZSBzYW1lIHF1ZXJ5L3NsdWcgaW4gYSBzaW5nbGUgc2Vzc2lvbiBcdTIwMTQgaW5kaWNhdGVzIHJldHJpZXZhbCBsb29wLiJ9XX0`

---

## Verification Notes

- `agentic_session` wraps the full generator including `[DONE]` sentinel — context stays open for entire stream (per common-mistakes.md)
- `user-retry` fires inside `agentic_session` context so `session_id` auto-resolves — no explicit `session_id=` parameter needed
- Tool signals fire inside the pydantic-ai tool context, which is inside the `agentic_session` context — `session_id` auto-resolves
- `useKeletSignal` is called inside `KeletProvider` (set up in `main.tsx`) — correct placement
- Copy button uses `styles.iconBtn` class — matches existing VoteFeedback icon button style exactly
- `beforeunload` handler has a guard (`sessionId && messages.length > 0`) to prevent spurious signals on fresh page loads
- No `source=SYNTHETIC` code written — all synthetic evaluation is via the platform deeplink
