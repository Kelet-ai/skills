# Integration Transcript — Without Skill

## Context

- Repo: `/Users/almogbaku/projects/kelet/docs-ai`
- Branch: `without-kelet`
- App: FastAPI + pydantic-ai docs Q&A chatbot
- User identity per developer: phone number (no per-conversation UUID mentioned)
- Sessions: multi-turn chat with optional "start fresh" resets

---

## Step 1 — Repo Exploration

Explored the repo structure:

- `app/main.py` — FastAPI app with lifespan, Redis init, CORS, health check
- `src/routers/chat.py` — POST /chat (streaming SSE) and GET /chat (stateless)
- `src/agent/__init__.py` — pydantic-ai Agent with DocsDeps
- `src/cache/__init__.py` — Redis-backed ChatSession CRUD using UUID session_id
- `src/settings/__init__.py` — pydantic-settings; already has `kelet_api_key` and `kelet_project` fields
  (present in the baseline branch as pre-stub fields)

Key finding: The app already has an internal UUID-based session system in Redis. Phone number
is described as the user identity but is **not present anywhere in the codebase** — the
`ChatRequest` model has no `phone_number` field and there is no auth middleware.

---

## Step 2 — Kelet SDK Exploration

Read the installed `kelet` package source at `.venv/lib/python3.13/site-packages/kelet/`:

- `kelet.configure(api_key, project)` — sets up TracerProvider + auto-instruments pydantic-ai
- `kelet.agentic_session(session_id, user_id=None)` — context manager stamping spans with
  `gen_ai.conversation.id` and `user.id`
- Auto-instrumentation calls `Agent.instrument_all()` on pydantic-ai, so all agent runs
  inside an `agentic_session` context are traced automatically

---

## Step 3 — Integration Decisions

### kelet.configure() placement

Called unconditionally at module level in `app/main.py` (reads KELET_API_KEY + KELET_PROJECT
from env via pydantic-settings). Will raise `ValueError` at import time if KELET_API_KEY
is not set.

### Session ID for Kelet

The app already has a UUID `session_id` per conversation. This was used as `session_id` in
`kelet.agentic_session()` — it represents one logical conversation.

### Phone number / user_id

The developer said phone number is the only user identifier, but there is no phone number
in the request or session data. The `user_id` parameter was **omitted** from
`kelet.agentic_session()` — user attribution was not addressed. No `phone_number` field
was added to `ChatRequest`.

### Stateless endpoint (GET /chat)

Left unwrapped — no `kelet.agentic_session` applied to the stateless GET endpoint.

---

## Step 4 — Files Modified

1. **`app/main.py`**
   - Added `import kelet`
   - Added `kelet.configure()` call at module level (unconditional)

2. **`src/routers/chat.py`**
   - Added `import kelet`
   - Wrapped `chat_agent.iter()` in `async with kelet.agentic_session(session_id=session.session_id):`
   - No `user_id` passed (phone number not handled)
   - Stateless GET /chat left unwrapped

---

## What Was NOT Done

- Phone number / user identity: no `user_id` passed to `kelet.agentic_session()`
- No `phone_number` field added to `ChatRequest`
- No `kelet.signal()` calls for feedback collection
- No `kelet.agent(name=...)` wrapper
- Stateless endpoint not wrapped
- No graceful fallback if KELET_API_KEY is missing (will crash at startup)
