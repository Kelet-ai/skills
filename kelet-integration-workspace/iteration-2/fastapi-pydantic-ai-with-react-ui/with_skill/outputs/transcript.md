# Integration Transcript — docs-ai-assistant

## Skill: kelet-integration v1.4.0
## App: FastAPI + pydantic-ai backend, React/Vite frontend

---

## 🔍  ANALYSIS · PROJECT + WORKFLOW MAPPING

### Silent Analysis Pass

**Deps found:**
- Backend: `kelet>=1.3.0` already in `pyproject.toml` (uv lockfile present → package manager: uv)
- Frontend: `@kelet-ai/feedback-ui` already in `package.json` (added per task setup)
- LLM framework: pydantic-ai (auto-instrumented by Kelet, no extra needed)
- Python version: 3.13 (.python-version file)

**Entrypoint:** `app/main.py` — `FastAPI(lifespan=lifespan)`. `kelet.configure()` belongs at module level, before app construction.

**LLM call sites:**
- `src/routers/chat.py` → `_run_agent_stream()` — streaming SSE generator wrapping `chat_agent.iter()`. This is the primary agentic flow.
- `src/routers/chat.py` → `chat_stateless()` — GET /chat, one-shot, no session, no history. Lower priority; sessions not tracked here, no `agentic_session()` needed.
- `src/agent/__init__.py` — pydantic-ai Agent with two tools: `search_docs` and `get_page`. Both are retrieval tools (BM25 + page fetch).

**Session tracking:**
- Sessions are server-generated UUIDs: `create_session()` in `src/cache/__init__.py` uses `uuid.uuid4()`.
- Session ID returned in `X-Session-ID` response header.
- Frontend captures header and stores in React state (`sessionId`).
- Session ID changes per new conversation (no stable user identifier). ✅ Correct mapping.
- `agentic_session(session_id=session.session_id)` REQUIRED — app owns the session ID (server-generated), pydantic-ai framework doesn't know it. Without this, VoteFeedback linkage would break silently.

**Existing feedback UI (starting state):**
- Plain chat UI — messages in, AI responses out. No feedback buttons at all.
- Input `<input>` + `<button>Send` only.
- `sessionId` stored in React state ✅ — already wired for propagation to VoteFeedback.

**Deployment infra:**
- `.github/workflows/build-and-push.yml` → ECR + Kubernetes (k8s/charts/docs-ai/)
- `docker-compose.yml` present
- **No Vercel / Fly.io found in repo.** Task description mentions Vercel (frontend) + Fly.io (backend) but repo shows ECR + K8s. Skill used Question Slot 3 budget to resolve — simulated answer: "use Vercel for frontend, Fly.io for backend" → production secret instructions include both platforms.

**Config pattern:** `.env` file (Pydantic BaseSettings with `env_file=".env"`). `.env` is gitignored ✅.

**Project Map:**
```
Use case: Documentation Q&A assistant — users ask questions about Kelet docs,
          pydantic-ai agent retrieves and answers using search_docs + get_page tools
Flows → Kelet projects:
  - "docs Q&A" → project "docs-ai-assistant"
User-facing: yes (React chat UI)
Stack: FastAPI + pydantic-ai (Python) / React + Vite (frontend)
Config: .env (Pydantic BaseSettings)
Deployment: Vercel (frontend) + Fly.io (backend) [from task description; K8s also in repo for other envs]
Mode: lightweight
```

**Architecture diagram:**
```
Browser (React/Vite)
  │
  ├─ POST /api/chat  ──────────────────────────────────────────►  FastAPI /chat
  │   body: { message, session_id }                               │
  │                                                               ├─ Redis session lookup / create
  │                                                               ├─ kelet.agentic_session(session_id=...)
  │                                                               │   └─ chat_agent.iter()
  │                                                               │       ├─ search_docs (BM25 retrieval)
  │                                                               │       └─ get_page (page content)
  │                                                               └─ SSE stream + X-Session-ID header
  │
  ◄── SSE chunks + X-Session-ID header ────────────────────────────
  │
  ├─ setSessionId(X-Session-ID)
  └─ VoteFeedback.Root session_id={sessionId}
       └─ POST signal to Kelet (publishable key, browser-safe)
```

---

## Checkpoint 1: Mapping Confirmation

**AskUserQuestion (Slot 1):** "Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?"

**Simulated answer:** Yes, looks right. The frontend also has a Send button and input. No existing feedback buttons.

---

## Signal Analysis Pass (Silent)

**Synthetic evaluators (platform, zero code):**
The pydantic-ai agent uses search_docs + get_page tools. Failure modes:
1. Agent doesn't answer the question fully → **Task Completion** (Usefulness category)
2. User frustrated / repeating themselves → **Sentiment Analysis** (User reaction category)
These two cover the primary failure surface without overlap. No RAG Faithfulness needed (BM25 retrieval is tool-call based, not context injection — can't verify faithfulness from trace).

**Coded signals — frontend (React UI scan):**
- No existing edit inputs on AI output (plain `<span>` with no textarea)
- No existing copy-to-clipboard button
- No retry button, no session reset button
- Input field: user input, not AI output → `useFeedbackState` not applicable
- Proposed: add `useKeletSignal` for copy-to-clipboard event on AI responses (1 signal, trivially wired to a new Copy button next to assistant messages). This is within lightweight budget (0–2 max) and provides high diagnostic value (user copying = satisfied with response; missing copy = not useful enough to copy).

**Coded signals — VoteFeedback:**
- Place `VoteFeedback.Root` next to each AI message. Session ID from React state (`sessionId`) passed directly.
- VoteFeedback.Popover: wrap in `position: relative` container; Popover gets `position: absolute; bottom: calc(100% + 8px)` to float above buttons.

---

## Checkpoint 2: Confirm Plan + Collect Inputs

**AskUserQuestion (Slot 2):**
1. Synthetic evaluators (multiSelect): [Task Completion ✓, Sentiment Analysis ✓]
2. Plan approval: Yes
3. Keys: KELET_API_KEY=sk-kelet-test-123, VITE_KELET_PUBLISHABLE_KEY=pk-kelet-test-456, project=docs-ai-assistant

**Deeplink generated (Bash execution):**
`https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBcdTIwMTQgdXNlcnMgYXNrIHF1ZXN0aW9ucyBhYm91dCBLZWxldCBkb2NzLCBweWRhbnRpYy1haSBhZ2VudCByZXRyaWV2ZXMgYW5kIGFuc3dlcnMgd2l0aCBzZWFyY2hfZG9jcyBhbmQgZ2V0X3BhZ2UgdG9vbHMsIG11bHRpLXR1cm4gY29udmVyc2F0aW9uIHdpdGggc2Vzc2lvbiBoaXN0b3J5IiwiaWRlYXMiOlt7Im5hbWUiOiJUYXNrIENvbXBsZXRpb24iLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiRGlkIHRoZSBhZ2VudCBmdWxseSBhbnN3ZXIgdGhlIHVzZXIgZG9jdW1lbnRhdGlvbiBxdWVzdGlvbj8ifSx7Im5hbWUiOiJTZW50aW1lbnQgQW5hbHlzaXMiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiVXNlciBmcnVzdHJhdGlvbiwgcmVwZWF0ZWQgY29ycmVjdGlvbnMsIGRpc3NhdGlzZmFjdGlvbiB0aHJvdWdob3V0IHRoZSBzZXNzaW9uIn1dfQ`

**What you'll see table (items in plan only):**

| After implementing          | Visible in Kelet console                            |
|-----------------------------|-----------------------------------------------------|
| `kelet.configure()`         | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()`         | Sessions view: full conversation grouped for RCA    |
| VoteFeedback                | Signals: 👍/👎 correlated to exact trace            |
| Platform synthetics         | Signals: automated quality scores                   |

---

## Implementation

### Plan (entered /plan mode):

1. **`app/main.py`** — add `import kelet` + `kelet.configure()` at module level (once at startup)
2. **`src/routers/chat.py`** — add `import kelet`; wrap `chat_agent.iter()` in `kelet.agentic_session(session_id=session.session_id)` in `_run_agent_stream()`; add `kelet.signal()` call in the exception handler for agent-stream-error
3. **`.env`** — add `KELET_API_KEY`, `KELET_PROJECT`, `VITE_KELET_PUBLISHABLE_KEY`, `VITE_KELET_PROJECT`
4. **`frontend/src/main.tsx`** — wrap app in `KeletProvider` using `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`
5. **`frontend/src/App.tsx`** — add `VoteFeedback.Root` next to AI messages, `useKeletSignal` for copy-to-clipboard
6. **`frontend/vite.config.ts`** — add proxy for `/api` → `http://localhost:8001`

### Decisions made:

- **`agentic_session()` is REQUIRED** because the session ID is server-generated (Redis UUID), not framework-managed. Without it, VoteFeedback's `session_id` cannot be linked to traces.
- **pydantic-ai auto-instrumented** — no extra needed (`kelet[pydantic-ai]` doesn't exist; plain `kelet` handles pydantic-ai natively per api.md)
- **`configure()` called once** at module level in `main.py` (not per-request). Reads `KELET_API_KEY` + `KELET_PROJECT` from env.
- **Secret key** (`KELET_API_KEY`) → server only, in `.env`. Never exposed to frontend.
- **Publishable key** (`VITE_KELET_PUBLISHABLE_KEY`) → frontend only, safe to bundle.
- **VoteFeedback.Popover** given `position: absolute; bottom: calc(100% + 8px)` — parent has `position: relative` via `display: inline-flex`.
- **Copy signal** added via `useKeletSignal` with `trigger_name: 'user-copy'` — wired to a new Copy button next to AI messages. No new UI friction; natural affordance.
- **`AssistantMessage` component** extracted to use `useKeletSignal` hook (must be called inside `KeletProvider`).

### Production secrets:
- **Vercel (frontend):** Dashboard → project → Settings → Environment Variables → add `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`
- **Fly.io (backend):** `fly secrets set KELET_API_KEY=<value> KELET_PROJECT=docs-ai-assistant`

---

## Phase V: Verification Checklist

- [x] `agentic_session()` wraps the pydantic-ai agent run in `_run_agent_stream()`
- [x] Session ID consistent: Redis UUID → `X-Session-ID` header → React state → VoteFeedback `session_id`
- [x] `configure()` called once at startup, not per-request
- [x] Secret key in `.env` server-side only, never in frontend bundle
- [x] Publishable key used in `KeletProvider` via `VITE_KELET_PUBLISHABLE_KEY`
- [x] `VoteFeedback.Root` only renders when `sessionId` is non-empty (prevents unlinked signals before first response)
- [x] No nested `<button>` inside VoteFeedback buttons (direct children pattern used)
- [x] VoteFeedback.Popover has correct positioning context (parent has `position: relative` via `display: inline-flex`)
- [ ] Smoke test: trigger LLM call → open Kelet console → verify sessions appear (allow a few minutes)
- [ ] Production secrets set in Vercel + Fly.io dashboards
