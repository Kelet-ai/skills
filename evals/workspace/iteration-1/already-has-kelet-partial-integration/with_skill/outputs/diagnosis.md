# Diagnosis: Why Sessions Were Not Appearing

## Symptom

Each LLM call appeared as a separate unlinked trace in the Kelet console. No sessions were visible.

---

## Root Cause 1: Missing `agentic_session()`

**File:** `src/routers/chat.py`

**What was there:** `import kelet` at the top, but kelet was never called during a chat request.

**Why `agentic_session()` is required for this app:**

The skill's Sessions section states:

> `agentic_session()` NOT required (auto-instrumented): [...] pydantic-ai [...]

However, this exception is overridden by:

> `agentic_session(session_id=...)` REQUIRED: **App owns the session ID** (Redis, DB, server-generated): framework doesn't know it → VoteFeedback linkage breaks

The app generates its own UUIDs in `src/cache/__init__.py`:
```python
session_id = str(uuid.uuid4())
```

These UUIDs are stored in Redis and returned to the browser as `X-Session-ID`. The pydantic-ai framework has no knowledge of this ID — it only sees individual `Agent.iter()` invocations. Without `agentic_session(session_id=session.session_id)`, Kelet has no way to associate the LLM span with the app's session.

The common-mistakes.md entry confirms the exact symptom:

| Mistake | Symptom |
|---|---|
| DIY orchestration without `agentic_session()` | Sessions appear fragmented — each LLM call is a separate unlinked trace in Kelet |

**Fix:** Wrap `chat_agent.iter()` inside `_run_agent_stream()` with:
```python
async with kelet.agentic_session(session_id=session.session_id):
    async with chat_agent.iter(...) as run:
        ...
```

---

## Root Cause 2: Wrong SDK Method Name (`kelet.init()`)

**File:** `app/main.py`

**What was there:**
```python
kelet.init(api_key=settings.kelet_api_key, project=settings.kelet_project)
```

**The problem:** `kelet.init()` is not a valid SDK method. The correct method is `kelet.configure()`. Because Kelet silences all SDK errors, this call fails silently — appearing to work while doing nothing.

**Fix:**
```python
kelet.configure()  # reads KELET_API_KEY + KELET_PROJECT from env
```
Or with explicit params:
```python
kelet.configure(api_key=settings.kelet_api_key, project=settings.kelet_project)
```

---

## Why This Was Silent

Both failures are explicitly listed in common-mistakes.md as silent:

> **Kelet never raises exceptions.** All SDK errors are silenced — a misconfigured integration looks identical to a working one.

- `kelet.init()` failed silently (unknown method, swallowed error)
- Missing `agentic_session()` means traces are emitted but with no session context — they appear in the Traces view but not grouped as Sessions

---

## What the Fix Enables

After the fix:

| Console view | What appears |
|---|---|
| Traces | LLM spans with model, tokens, latency (was already working once configure() is fixed) |
| Sessions | Full conversation grouped for RCA — multiple turns linked by session UUID |

---

## Scope Decision: GET /chat Not Wrapped

The stateless `GET /chat` endpoint is intentionally not wrapped with `agentic_session()`. It is documented as "one-shot, no session, no history" and is used for curl/tool access. Wrapping it would create misleading single-span sessions and is not aligned with the app's intent.
