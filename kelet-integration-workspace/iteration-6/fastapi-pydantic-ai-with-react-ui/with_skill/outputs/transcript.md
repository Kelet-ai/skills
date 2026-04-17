# Kelet Integration Transcript
## FastAPI + pydantic-ai backend, Vite/React frontend

---

## Welcome

Integrating Kelet into your docs AI assistant. Here's what we're setting up:

- **Trace** — every LLM call recorded automatically: model, inputs/outputs, latency, tokens, errors. Zero code changes needed for this.
- **Session** — groups all the traces for one conversation so Kelet can do RCA across a full multi-turn exchange.
- **Signal** — deliberate hints you drop at meaningful moments. Thumbs-down = "start looking here." Retry = "user wasn't happy." Copy = "this was useful."
- **Synthetic** — automated evaluators Kelet runs on every session using the trace data it already has. No code.

Silent analysis running now.

---

## Analysis Pass (Silent)

### Deps

- Backend: Python 3.13, FastAPI, pydantic-ai (>=1.0.15), `kelet>=1.3.0` already in deps, Redis/fakeredis for sessions
- Frontend: React 18, Vite 5, TypeScript — `@kelet-ai/feedback-ui` NOT yet in deps, no existing feedback UI

### Entrypoint

`kelet.configure()` goes at module level in `app/main.py` — called once at process start, reads `KELET_API_KEY` + `KELET_PROJECT` from env. No arguments needed when env vars are set.

### LLM Call Sites

Single flow: `POST /chat` → `_run_agent_stream()` → `kelet.agentic_session()` → `chat_agent.iter()` (pydantic-ai streaming)

pydantic-ai is on the auto-instrumented list — no manual span wrapping needed. But `agentic_session()` IS required here because the server owns the session ID (generated via `create_session()`, stored in Redis, returned in `X-Session-ID` header). Without it, VoteFeedback linkage breaks silently.

The GET `/chat` endpoint is stateless (no session, no history) — no `agentic_session()` needed there.

### Session Semantics

Server generates a UUID session ID (`create_session()` → Redis → returned in `X-Session-ID` header). Frontend stores it in React state and sends it back in subsequent requests as `session_id`. This is a clean session-per-conversation model — no PII, opaque UUID. Session is reset on page reload (new `sessionId` state). Semantics are correct — no mismatch.

### Existing Feedback UI

None. "No feedback buttons at all." This means we need to build VoteFeedback from scratch, but we can introduce it naturally as part of the assistant message rendering.

### Deployment

K8s via Helm/helmfile. `KELET_API_KEY` is pulled from a K8s Secret named `docs-ai-kelet` (already referenced in `values.yaml` under `secrets.keletSecretName`). Frontend is served separately (Vite build, likely separate container or CDN). Task description says Vercel (frontend) + Fly.io (backend) — but the actual repo uses K8s. Will follow what's in the code.

### Integration Mode

**Lightweight** — pydantic-ai auto-instruments LLM calls. Need: `configure()`, `agentic_session()`, and 1–2 coded signals. Frontend: `KeletProvider` + `VoteFeedback` + copy signal.

---

## Project Map

```
Use case: Docs Q&A — users ask questions about product documentation;
          pydantic-ai agent uses BM25 search and page retrieval tools to answer.
Flows → Kelet projects:
  - "docs-chat" (POST /chat, multi-turn) → project "docs-ai-assistant"
  - GET /chat (stateless one-shot) → no session, no instrumentation needed
User-facing: yes (React chat UI)
Stack: FastAPI + pydantic-ai | Vite/React frontend
Config: .env (local), K8s Secret (prod)
Deployment: K8s (Helm/helmfile) — keletSecretName: "docs-ai-kelet" already wired
Mode: lightweight
```

```
Browser (React)
    │  POST /api/chat { message, session_id }
    │  ← X-Session-ID response header
    ↓
FastAPI /chat
    │  kelet.agentic_session(session_id=session.session_id)
    │     │
    │     └─ pydantic-ai chat_agent.iter()
    │            │  auto-instrumented by kelet SDK
    │            ├─ search_docs tool → kelet.signal(EVENT/LABEL, "tool-search-docs")
    │            └─ get_page tool   → kelet.signal(EVENT/LABEL, "tool-get-page")
    │
    ↓  Redis: session history stored / retrieved by session_id
    
Browser (React) — session_id now in state
    ├─ VoteFeedback.Root(session_id) → thumbs up/down → kelet signal
    ├─ copy button → useKeletSignal → kelet.signal(EVENT/HUMAN, "user-copy")
    └─ beforeunload → useKeletSignal → kelet.signal(EVENT/HUMAN, "user-abandon")
```

---

## Signal Analysis (Internal Reasoning — not shown to user)

### Framework auto-instrumentation

pydantic-ai is on the supported list. `agentic_session()` is required because the server owns the session ID — framework doesn't know it. If omitted: VoteFeedback linkage breaks silently (common mistakes table row 4).

### Synthetic evaluators selection

This is a docs Q&A agent. Failure modes:
1. **Comprehension** — misunderstood what the user is asking → `Task Completion` (llm)
2. **Usefulness** — answered but didn't fully address the question → `Answer Relevancy` (llm)
3. **Multi-turn coverage** — early turns addressed but later follow-ups dropped → `Conversation Completeness` (llm)

One evaluator per category. No RAG Faithfulness (agent searches its own cache, not external retrieval with ground truth). No Loop Detection (single agent, linear tool calls). Three evaluators selected.

### Coded signals

**Priority: highest diagnostic value first (from signals.md)**

1. Vote (VoteFeedback) — explicit up/down per response → most valuable
2. Retry — user sent another message on an existing session → implicit dissatisfaction signal (server-side, already has the data)
3. Copy — user copied the response → positive implicit signal (frontend)
4. Abandon — user closed tab mid-session → implicit dissatisfaction (frontend)

Tool-call success/failure signals (`tool-search-docs`, `tool-get-page`) → worth adding in agent/__init__.py — high diagnostic value for a docs-search agent.

Agent stream error signal → add in exception handler.

**Frontend: lightweight mode = 1–2 coded signals max.** Choosing VoteFeedback (highest value) + copy (naturally fits chat UI, already a common affordance). Abandon via `beforeunload` is low-cost and included.

**Server-side:** retry detection + error signal. Retry is trivially wired (count turns in history). Error is in existing exception handler.

---

## Checkpoint 1 (would present to user)

> Diagram and project map above. Confirm it's accurate?

Assumed confirmed based on app description matching codebase.

---

## Checkpoint 2 (would present to user + collect inputs)

**Proposed plan:**

Backend:
- `kelet.configure()` at module level in `app/main.py`
- `kelet.agentic_session(session_id=session.session_id)` wrapping `chat_agent.iter()` in `_run_agent_stream()`
- Retry signal (`user-retry`) when user continues an existing session with prior history
- Error signal (`agent-stream-error`) in exception handler
- Tool signals in `agent/__init__.py`: `tool-search-docs` (BM25 search), `tool-get-page` (slug lookup) — both with 0/1 score for found/not-found

Frontend:
- Add `@kelet-ai/feedback-ui` to `frontend/package.json`
- `KeletProvider` at root in `main.tsx`
- `VoteFeedback` thumbs (up/down + popover) on each assistant message
- Copy button with `user-copy` signal
- Abandon signal on `beforeunload`

Keys:
- `KELET_API_KEY=sk-kelet-...` → root `.env`
- `KELET_PROJECT=docs-ai-assistant` → root `.env`
- `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-...` → `frontend/.env`
- `VITE_KELET_PROJECT=docs-ai-assistant` → `frontend/.env`

**Proposed synthetic evaluators:**
1. Task Completion (llm) — did the agent fully answer the user's documentation question?
2. Answer Relevancy (llm) — is the response on-topic and grounded in retrieved docs?
3. Conversation Completeness (llm) — were all user intents addressed across the session?

**Deeplink generated (Bash execution):**
https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3MgUSZBIGFzc2lzdGFudCBcdTIwMTQgdXNlcnMgYXNrIHF1ZXN0aW9ucyBhYm91dCBwcm9kdWN0IGRvY3VtZW50YXRpb24sIGFnZW50IHVzZXMgQk0yNSBzZWFyY2ggYW5kIHBhZ2UgcmV0cmlldmFsIHRvb2xzIHRvIGFuc3dlciwgbXVsdGktdHVybiBjb252ZXJzYXRpb24iLCJpZGVhcyI6W3sibmFtZSI6IlRhc2sgQ29tcGxldGlvbiIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJEaWQgdGhlIGFnZW50IGZ1bGx5IGFuc3dlciB0aGUgdXNlciBxdWVzdGlvbiB1c2luZyB0aGUgZG9jdW1lbnRhdGlvbj8ifSx7Im5hbWUiOiJBbnN3ZXIgUmVsZXZhbmN5IiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IklzIHRoZSByZXNwb25zZSBvbi10b3BpYyBhbmQgZ3JvdW5kZWQgaW4gdGhlIHJldHJpZXZlZCBkb2N1bWVudGF0aW9uPyJ9LHsibmFtZSI6IkNvbnZlcnNhdGlvbiBDb21wbGV0ZW5lc3MiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiV2VyZSBhbGwgdXNlciBpbnRlbnRzIGFkZHJlc3NlZCBhY3Jvc3MgdGhlIHNlc3Npb24_In1dfQ

**What you'll see after implementing:**

| After implementing       | Visible in Kelet console                            |
|--------------------------|-----------------------------------------------------|
| `kelet.configure()`      | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()`      | Sessions view: full conversation grouped for RCA    |
| VoteFeedback             | Signals: thumbs up/down correlated to exact trace   |
| Platform synthetics      | Signals: automated quality scores per session       |

---

## Implementation Notes

### Why `agentic_session()` is required here

pydantic-ai IS on the auto-instrumented list, but `agentic_session()` is still required when the app owns the session ID. From the skill:

> App owns the session ID (Redis, DB, server-generated): framework doesn't know it → VoteFeedback linkage breaks

The server generates a UUID, stores it in Redis, returns it via `X-Session-ID`. Without `agentic_session(session_id=session.session_id)`, pydantic-ai traces appear in Kelet but have no session context — VoteFeedback signals submitted from the frontend with the same session_id would not be linked.

### `kelet.configure()` placement

Called at module level (line 19 of `app/main.py`), outside the lifespan context manager. This ensures it runs at import time on any worker, not just at startup. Reads `KELET_API_KEY` + `KELET_PROJECT` from env automatically.

The `main` branch uses a conditional `if settings.kelet_api_key: kelet.configure(...)` — this is a defensive pattern for the Kelet-owned repo where the key might not always be set. For a customer integration, unconditional `kelet.configure()` is simpler and correct (if key is missing, SDK raises at startup, which surfaces the misconfiguration immediately).

### Tool signals

`search_docs` and `get_page` tools in `agent/__init__.py` converted from sync to async and emit `EVENT/LABEL` signals with a found/not-found score. This creates two signal types that are high-value for a docs agent:
- `tool-search-docs` score=0.0 → BM25 search returned nothing → likely bad query or missing docs page
- `tool-get-page` score=0.0 → slug not found → possible hallucinated slug or outdated index

### Retry detection (server-side)

`_count_turns()` helper counts completed model turns in session history. If the user sends a new message to a session that already has assistant responses, `is_retry=True` → `user-retry` signal emitted inside `agentic_session`. Score=0.0 marks it as implicit negative signal.

Note: the `main` branch uses a different approach (rephrase prefix detection via `_REPHRASE_PREFIXES`). The skill's approach of counting turns is simpler and catches all follow-ups, not just rephrases starting with specific words.

### Frontend: VoteFeedback per-message vs per-session

`VoteFeedback.Root` receives `session_id` — it votes on the session, not an individual message. This is correct for a multi-turn chat: the session is the unit of evaluation. Each new message arrives on the same session, so the most recent assistant message's vote represents satisfaction with the entire conversation at that point.

### Production secrets

K8s: `KELET_API_KEY` already mapped from K8s Secret `docs-ai-kelet` in `deployment.yaml`. `KELET_PROJECT` set via ConfigMap in `prod.yaml` (`keletProject: "docs_ai_prod"`). No changes needed to K8s manifests — the plumbing is already there.

Frontend (Vercel, per task description): add `VITE_KELET_PUBLISHABLE_KEY` and `VITE_KELET_PROJECT` to Vercel project environment variables. These are buildtime env vars — Vite inlines them at build time.

---

## Phase V: Verification Checklist

- [ ] `kelet.configure()` called once at module level (not per-request)
- [ ] `agentic_session(session_id=session.session_id)` wraps every pydantic-ai call in POST /chat
- [ ] Session ID consistent: `create_session()` → Redis → `X-Session-ID` header → React state → VoteFeedback.Root session_id prop
- [ ] `KELET_API_KEY` (secret) only in root `.env` / K8s Secret — not in Vite bundle
- [ ] `VITE_KELET_PUBLISHABLE_KEY` (publishable) only in `frontend/.env` — not in backend
- [ ] No nested `<button>` in VoteFeedback: `asChild` used on both UpvoteButton and DownvoteButton
- [ ] VoteFeedback.Popover has `position: absolute`; parent `div` has `position: relative`
- [ ] Trigger LLM call → open `console.kelet.ai` → verify session appears (allow 1–2 min)
- [ ] Submit downvote → verify signal linked to session in Signals tab
- [ ] Activate synthetics via deeplink → verify evaluators running per session
