# Skill Execution Transcript
**Prompt:** "I already have kelet installed but I'm not seeing sessions in the console"
**App:** FastAPI + pydantic-ai docs Q&A service

---

## 🔍  ANALYSIS · PROJECT + WORKFLOW MAPPING

### Silent Analysis Pass

**Deps scan:**
- `kelet>=1.3.0` in `pyproject.toml` — confirmed installed
- `pydantic-ai>=1.0.15` — auto-instrumented framework (no peer deps needed)
- `fastapi`, `uvicorn`, `redis[asyncio]` — server stack
- No frontend UI package (`@kelet-ai/feedback-ui` absent) → lightweight mode default

**Entrypoint:** `app/main.py` — `lifespan()` context manager manages startup/shutdown. This is where `configure()` belongs.

**Finding 1 — `configure()` is absent:**
`app/main.py` has no `import kelet` and no `kelet.configure()` call. The `.env` file contains `KELET_API_KEY=sk-kelet-test-123` and `KELET_PROJECT=docs-ai-assistant` but nothing reads them at startup. The Settings model has `kelet_api_key` and `kelet_project` fields already wired.

**Finding 2 — `agentic_session()` is absent:**
`src/routers/chat.py` runs `chat_agent.iter(...)` with no session wrapper. pydantic-ai is listed as auto-instrumented, but the rule applies with a critical caveat: **"App owns the session ID"** — this app generates session IDs in `cache/__init__.py` using `uuid.uuid4()`, stores them in Redis, and passes them through the POST `/chat` endpoint. pydantic-ai has no knowledge of these IDs. Without `agentic_session(session_id=session.session_id)`, each LLM call produces an unlinked trace — exactly the reported symptom.

**Session semantics check:**
- Sessions are created per-conversation: `create_session()` → `uuid4()` stored in Redis with a 30-minute TTL
- `X-Session-ID` response header already exposes the session ID to the frontend
- Session IDs reset on expiry or when client sends no `session_id` — correct semantics
- `agentic_session()` must wrap the agent call using `session.session_id`

**Deployment infra:** Kubernetes via Helm (`k8s/charts/docs-ai/`). ConfigMap template has `KELET_PROJECT`, Deployment template reads `KELET_API_KEY` from a Kubernetes Secret (`secrets.keletSecretName`). Infrastructure is already wired — no secrets changes needed.

**Mode decision:** Lightweight. No frontend, no existing feedback UI, developer asked a targeted fix question.

**Project Map:**
```
Use case: Docs Q&A — answers questions about Kelet documentation
Flows → Kelet projects:
  - POST /chat  → project "docs-ai-assistant" (stateful, session-aware)
  - GET /chat   → project "docs-ai-assistant" (stateless, no session — not wrapped)
User-facing: yes (SSE streaming responses to browser clients)
Stack: FastAPI + pydantic-ai + Redis
Config: .env (dev) / K8s ConfigMap + Secret (prod)
Deployment: Kubernetes (Helm)
Mode: lightweight
```

**Architecture:**
```
Browser
  │  POST /chat {message, session_id?}
  ▼
FastAPI /chat endpoint
  │  get_session() / create_session() → Redis (TTL 30min)
  │  session.session_id = <uuid4>
  ▼
_run_agent_stream()
  │  [MISSING] kelet.agentic_session(session_id=session.session_id)
  ▼
chat_agent.iter()  ← pydantic-ai auto-instruments LLM spans
  │  tool calls: search_docs(), get_page()
  ▼
Bedrock (claude-sonnet-4-6)
  │
  ▼
Kelet collector  ← spans arrive here, but no session context
                   → each call appears as unlinked trace
```

---

## Diagnosis

**Root cause:** Two missing pieces, both silent:

1. **`kelet.configure()` never called** → SDK is installed but not initialized. No spans are exported at all.
2. **`agentic_session()` absent** → Even after fixing (1), pydantic-ai spans won't be grouped into sessions because the framework has no knowledge of the app-owned session ID.

The second issue is why the developer sees "sessions" missing rather than "traces missing" — pydantic-ai auto-instrumentation would fire once configure() is called, but every turn would appear as a disconnected trace instead of a session.

**What was NOT a problem:**
- `kelet` is correctly in deps — no install needed
- `.env` has the keys — no new secrets needed
- Settings model already has `kelet_api_key` and `kelet_project` — no settings changes needed
- K8s infrastructure already injects `KELET_API_KEY` from a Secret and `KELET_PROJECT` from ConfigMap — production is ready once code is fixed
- pydantic-ai does NOT need `kelet[pydantic-ai]` extra — plain `kelet` is correct

---

## Signal Analysis (Internal)

**Synthetic candidates** (platform-managed, no code):
- `Task Completion` — did the agent answer the docs question?
- `Answer Relevancy` — did it stay on-topic (allowed_topics="Kelet")?
- `Conversation Completeness` — multi-turn: did user leave with their question answered?

**Coded signals** (lightweight, 0–1 max):
- The app detects user corrections implicitly (`_REPHRASE_PREFIXES` exists in main branch) — a `user-correction` signal on message rephrase is natural and already modeled in the codebase. Worth proposing as a single lightweight coded signal.

---

## Plan Presented at Checkpoint 2

**Fix 1: `app/main.py`** — add `import kelet`, call `kelet.configure()` in lifespan using existing settings fields, add `kelet.shutdown()` at teardown to flush the BatchSpanProcessor.

**Fix 2: `src/routers/chat.py`** — add `import kelet`, wrap `chat_agent.iter(...)` with `async with kelet.agentic_session(session_id=session.session_id):`. The entire generator body including `[DONE]` sentinel must be inside the context manager to avoid incomplete traces.

**No changes to:**
- `settings/__init__.py` — already has `kelet_api_key` and `kelet_project`
- `.env` — already has correct keys
- `k8s/` — already has correct secret/configmap wiring
- `pyproject.toml` — `kelet>=1.3.0` is correct, no extras needed for pydantic-ai

**Synthetic deeplink** (generated with Bash, not shown as code block):
URL presented to developer for `Task Completion`, `Answer Relevancy`, and `Conversation Completeness` evaluators against project `docs-ai-assistant`.

---

## Implementation

### `app/main.py` changes
- Added `import kelet` at module level
- Added `kelet.configure(api_key=settings.kelet_api_key, project=settings.kelet_project)` inside `lifespan()` before `docs_cache.start()`, guarded by `if settings.kelet_api_key:` to preserve graceful dev-mode behavior
- Added `kelet.shutdown()` in lifespan teardown (same guard) to flush spans before exit

### `src/routers/chat.py` changes
- Added `import kelet`
- Wrapped the entire `_run_agent_stream` body (agent iter, error handler, session save, `[DONE]` yield) with `async with kelet.agentic_session(session_id=session.session_id):`
- The `[DONE]` sentinel is inside the context manager — this is correct; closing the session context before `[DONE]` would produce incomplete traces

**Skipped:** stateless `GET /chat` endpoint — it has no `session` object and is explicitly documented as "no session, no history". Wrapping it would require generating a throwaway session ID per request, adding noise with no value.

---

## Phase V: Verification Checklist

- [x] `configure()` called once at startup (lifespan), not per-request
- [x] `agentic_session()` wraps every stateful agent entry point (`_run_agent_stream`)
- [x] Session ID is the app's own Redis-backed UUID — consistent end-to-end
- [x] Secret key (`KELET_API_KEY`) is server-only — never in frontend bundle
- [x] No `kelet[pydantic-ai]` extra used — correct, plain `kelet` is right
- [x] common-mistakes check: pydantic-ai exposes agent names natively — no manual `kelet.agent()` needed
- [ ] Smoke test: trigger POST /chat → open Kelet console → verify session appears (allow a few minutes)
