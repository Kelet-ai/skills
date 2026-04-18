# Transcript — Kelet Integration (fallback deeplink, can't paste secrets)

**Repo:** `/Users/almogbaku/projects/kelet/docs-ai`
**Branch:** `without-kelet` (pristine)
**Developer prompt:** "integrate kelet into my app"
**Stack detected:** FastAPI + pydantic-ai + Redis, plain HTML (no React), Fly.io deploy

---

## 👋 Welcome

> **Kelet** is an AI agent that performs Root Cause Analysis on AI app failures — it ingests traces + signals, clusters failure patterns, and suggests fixes.
>
> Quick concept primer so the rest makes sense:
>
> - **Trace** — one LLM call or tool invocation. `kelet.configure()` captures these automatically.
> - **Session** — traces grouped into one unit of work (one conversation). This is how Kelet correlates what happened.
> - **Signal** — a tip dropped at a meaningful moment. 👎 = start looking here. Edit = close but wrong. Abandon = gave up.
> - **Synthetic** — signal Kelet derives from trace data automatically (zero code).
> - **Project** — one logical boundary per agentic use case. Wrong project = invisible in RCA.
>
> What's ahead: I'll read your code silently, then ask at most 2 questions.

---

## 🧠 Silent Analysis Pass

Files read (no questions yet):

- `pyproject.toml` → FastAPI 0.115, pydantic-ai 1.0.15, Redis 5.2, `kelet>=1.3.0` already in deps. Python 3.13. uv lockfile.
- `app/main.py` → FastAPI entrypoint with `lifespan`, Redis (or FakeRedis fallback) in `app.state.redis`, CORS exposes `X-Session-ID`.
- `src/routers/chat.py` → two endpoints:
  - `POST /chat` — SSE stream, persistent session (Redis), session ID server-generated + returned in `X-Session-ID` header.
  - `GET /chat` — stateless one-shot plain text.
  - Both call `chat_agent.iter(...)` (pydantic-ai).
- `src/cache/__init__.py` → `ChatSession(session_id, history)`, `session_id = str(uuid.uuid4())` minted in `create_session`. Good — already opaque, non-PII, regenerates on new conversation.
- `src/agent/__init__.py` → pydantic-ai `Agent` with tools `search_docs` (BM25) and `get_page`. RAG-style retrieval over `llms.txt`.
- `frontend/` → empty (only `.env`). Confirmed: **plain HTML served by FastAPI, no React.**
- `k8s/`, Dockerfiles, `docker-compose.yml` present — and Fly.io is the declared deploy target (per integration context).
- `.env` / `.env.example` → will write config here.

### 🗺 Project Map

```
Use case: Kelet docs Q&A assistant (single agentic flow)
Flows → Kelet projects:
  - flow "docs-chat" → project "docs-ai-fallback"
User-facing: yes (plain HTML, no React)
Stack: FastAPI + pydantic-ai + Redis (FakeRedis fallback)
Config: .env (local) + Fly.io secrets (prod)
Deployment: Fly.io
Mode: lightweight
```

### 🏗 Architecture

```
     Browser (plain HTML)
            │
            │  POST /chat  { message, session_id? }
            ▼
   ┌────────────────────────┐
   │   FastAPI  (app/main)  │
   │  kelet.configure()     │  ← startup, reads KELET_* env
   └──────────┬─────────────┘
              │
              ▼
   ┌──────────────────────────────────────────┐
   │  routers/chat.py  — POST /chat           │
   │  ┌──────────────────────────────────┐    │
   │  │ session = redis.get_or_create()  │    │
   │  │ session.session_id = uuid4()     │    │
   │  │                                  │    │
   │  │ kelet.agentic_session(           │    │
   │  │     session_id=session.session_id│ ← groups all LLM spans
   │  │ ):                               │    │
   │  │     chat_agent.iter(...)         │    │   pydantic-ai
   │  │       → Bedrock Claude Sonnet    │    │   (auto-instrumented)
   │  │       → tools: search_docs, get_page
   │  └──────────────────────────────────┘    │
   │  response headers: X-Session-ID          │
   └──────────────────────────────────────────┘
              │
              ▼
      Redis (docs-ai:session:<id>)
```

**Session semantics note:** `session_id` is server-generated (`uuid4`), stored in Redis, and returned in `X-Session-ID`. pydantic-ai is auto-instrumented but does **not** know this ID — so `agentic_session(session_id=...)` is required to link LLM spans to the Kelet session.

**User identity:** the app has no stable user identity — no login, no email, no phone. So no `user_id=` is passed, and there is no PII concern to flag.

---

## 📍 Progress: Analysis ✅ → Checkpoint 1 🔄 → Signal Analysis ○ → Checkpoint 2 ○ → impl ○

## ✅ Checkpoint 1 — Mapping Confirmation

**AskUserQuestion:**
> Does this diagram, project map, and workflow summary accurately represent your system? Anything I missed?

Options: `Looks right — proceed.` · `Correction needed.`

**Developer:** Looks right — proceed.

---

## 🧠 Signal Analysis (internal — not shown to developer)

- **Synthetic candidates** (all derivable from traces):
  - `Task Completion` — universal anchor.
  - `RAG Faithfulness` — app retrieves docs pages; perfect fit.
  - `Answer Relevancy` — catches off-topic/padding.
  - `Hallucination Detection` — catches fabricated APIs with no retrieval context.
  - `Session Health Stats` — token/turn/tool-call structural anomalies (code type).
- **Coded signal candidates:** none — plain HTML with no existing feedback UI, no copy/retry/edit affordance. Lightweight mode; do not invent UI just to wire a signal.
- **VoteFeedback:** skip — requires React.

---

## 📍 Progress: Analysis ✅ → Checkpoint 1 ✅ → Signal Analysis ✅ → Checkpoint 2 🔄 → impl ○

## 📋 Checkpoint 2 — Plan + Inputs

### Proposed plan (lightweight)

1. Add `import kelet` + `kelet.configure()` to `app/main.py` (runs once at startup; reads `KELET_API_KEY` + `KELET_PROJECT` from env).
2. Wrap `chat_agent.iter(...)` in `src/routers/chat.py` with `async with kelet.agentic_session(session_id=session.session_id):` — server owns the session ID, pydantic-ai can't see it otherwise.
3. Also wrap the stateless `GET /chat` with `kelet.agentic_session(session_id=str(uuid.uuid4()))` so one-shot spans still group under a session.
4. Update `.env` + `.env.example`: `KELET_PROJECT=docs-ai-fallback`, `KELET_API_KEY` left as a commented placeholder (set via `fly secrets set KELET_API_KEY=sk-...` before deploy).
5. No frontend changes (plain HTML).
6. No coded signals in the lightweight plan.
7. Synthetic evaluators — 5 proposed, developer picks which apply.

### What you'll see in the console

| After implementing                                    | Visible in Kelet console                              |
| ----------------------------------------------------- | ----------------------------------------------------- |
| `kelet.configure()`                                   | LLM spans in Traces: model, tokens, latency, errors   |
| `agentic_session(session_id=session.session_id)`      | Sessions view: full conversation grouped for RCA      |
| Platform synthetics (picked below)                    | Signals: automated quality scores per session         |

### AskUserQuestion (multiSelect)

**1. Pick the synthetic evaluators to create:**
- [x] Task Completion (llm)
- [x] RAG Faithfulness (llm)
- [x] Answer Relevancy (llm)
- [x] Hallucination Detection (llm)
- [x] Session Health Stats (code)
- [ ] None

**2. Plan approval:** Does the rest of the plan look right?
**3. Project name:** `docs-ai-fallback` (reminder: create it first at console.kelet.ai → New Project — exact name match is required, or you'll hit a silent 404).
**4. API key mode:**
- Paste secret key (`sk-kelet-...`) — primary path.
- I'll grab one.
- **I can't paste secrets here.**

**Developer:**
- Evaluators: all 5 selected.
- Plan: approved.
- Project: `docs-ai-fallback`.
- Key mode: **"I can't paste secrets here"** — "I don't want to paste secrets into this terminal session, can we do it another way?"

---

## ⚠️ Fallback path (no API key)

Understood — no secret pasted. Switching to the **deeplink fallback**.

Important caveats (surfacing explicitly):

> ⚠️ **I cannot verify that the project `docs-ai-fallback` exists** without a key. Please make sure the name in the link below **exactly matches** the project you created at console.kelet.ai. A wrong name is a silent routing failure — your traces will upload but be invisible in RCA.
>
> ⚠️ **No automatic evaluator creation.** The link opens the console with your 5 evaluators pre-filled — you still need to click through to create them there.

### 👉 Open Kelet synthetic setup

**[Open Kelet synthetic setup → docs-ai-fallback](https://console.kelet.ai/docs-ai-fallback/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBhbnN3ZXJpbmcgcXVlc3Rpb25zIGFib3V0IEtlbGV0IGRvY3MgdmlhIHB5ZGFudGljLWFpICsgQk0yNSByZXRyaWV2YWwgb3ZlciBsbG1zLnR4dCIsImlkZWFzIjpbeyJuYW1lIjoiVGFzayBDb21wbGV0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgYW5zd2VyIHRoZSB1c2VyJ3MgZG9jdW1lbnRhdGlvbiBxdWVzdGlvbiBjb21wbGV0ZWx5IGFuZCBhY2N1cmF0ZWx5PyJ9LHsibmFtZSI6IlJBRyBGYWl0aGZ1bG5lc3MiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiQXJlIGNsYWltcyBncm91bmRlZCBpbiB0aGUgcmV0cmlldmVkIGRvY3MgcGFnZXMsIHdpdGggbm8gZmFicmljYXRpb24gYmV5b25kIGNvbnRleHQ_In0seyJuYW1lIjoiQW5zd2VyIFJlbGV2YW5jeSIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJJcyB0aGUgcmVzcG9uc2Ugb24tdG9waWMgZm9yIHRoZSBkb2NzIHF1ZXN0aW9uLCB3aXRob3V0IHBhZGRpbmcgb3IgZGVmbGVjdGlvbj8ifSx7Im5hbWUiOiJIYWxsdWNpbmF0aW9uIERldGVjdGlvbiIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJDYXRjaCBmYWJyaWNhdGVkIEFQSXMsIG5vbi1leGlzdGVudCBvcHRpb25zLCBvciBpbnZlbnRlZCBjaXRhdGlvbnMgb3V0c2lkZSB0aGUgZG9jcyBjb3JwdXMuIn0seyJuYW1lIjoiU2Vzc2lvbiBIZWFsdGggU3RhdHMiLCJldmFsdWF0b3JfdHlwZSI6ImNvZGUiLCJkZXNjcmlwdGlvbiI6IlR1cm4gY291bnRzLCB0b2tlbiB1c2FnZSwgYW5kIHRvb2wtY2FsbCBmcmVxdWVuY3kgXHUyMDE0IHN0cnVjdHVyYWwgYW5vbWFsaWVzIGluIGEgZG9jcyBRJkEgc2Vzc2lvbi4ifV19)**

No network call was made from this session — no `curl` to `api.kelet.ai`. The link above is a pure client-side deeplink with a base64url-encoded payload. Click it, review, and click "Create" in the console.

Deeplink payload (pre-base64) for reference:

```json
{
  "use_case": "Documentation Q&A assistant answering questions about Kelet docs via pydantic-ai + BM25 retrieval over llms.txt",
  "ideas": [
    {"name": "Task Completion", "evaluator_type": "llm", "description": "..."},
    {"name": "RAG Faithfulness", "evaluator_type": "llm", "description": "..."},
    {"name": "Answer Relevancy", "evaluator_type": "llm", "description": "..."},
    {"name": "Hallucination Detection", "evaluator_type": "llm", "description": "..."},
    {"name": "Session Health Stats", "evaluator_type": "code", "description": "..."}
  ]
}
```

---

## 🛠 Implementation (lightweight)

Entered `/plan` mode, presented the plan, got `ExitPlanMode` approval, then applied:

### `app/main.py`

```python
import kelet
# ...
kelet.configure()  # reads KELET_API_KEY + KELET_PROJECT at call time
```

### `src/routers/chat.py`

POST /chat wraps the pydantic-ai run:

```python
async with kelet.agentic_session(session_id=session.session_id):
    async with chat_agent.iter(message, deps=deps, message_history=message_history) as run:
        ...
```

GET /chat (stateless) also gets a short-lived session:

```python
async with kelet.agentic_session(session_id=str(uuid.uuid4())):
    async with chat_agent.iter(q, deps=deps) as run:
        ...
```

### `.env` + `.env.example`

```
KELET_PROJECT=docs-ai-fallback
# KELET_API_KEY — set via: fly secrets set KELET_API_KEY=sk-kelet-...
```

(`.env` is in `.gitignore`.)

### Fly.io deployment note

Before deploying:

```
fly secrets set KELET_API_KEY=sk-kelet-your-real-key KELET_PROJECT=docs-ai-fallback
```

---

## 🕵️ Phase V — Verification (silent-failure checklist)

- ✅ `agentic_session(session_id=session.session_id)` covers POST /chat where the app owns the session ID.
- ✅ Stateless GET /chat also wrapped — spans won't appear unlinked.
- ✅ `kelet.configure()` called once at module import (startup), not per-request.
- ✅ No secret key in the frontend bundle — there is no frontend bundle.
- ✅ `.env` is gitignored; production uses `fly secrets`.
- ⚠️ Cannot smoke-test the console path — developer declined to paste a key. Next step for them: open the deeplink, create the evaluators, trigger a chat, confirm sessions appear at `https://console.kelet.ai/docs-ai-fallback/sessions` (give it a few minutes).
- ⚠️ Project name unverified (no API check possible) — silent 404 risk if the name doesn't match.

## ✅ Done

Summary delivered to developer:

- 2 files changed in code (`app/main.py`, `src/routers/chat.py`) + 2 env files.
- No `curl` to `api.kelet.ai` was issued (fallback path).
- One clickable deeplink to finish synthetic evaluator setup in the console.
- Two explicit warnings surfaced: project name is unverified; evaluators still require a click-through.
