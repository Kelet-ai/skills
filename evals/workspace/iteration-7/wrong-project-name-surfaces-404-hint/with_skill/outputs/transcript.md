# Kelet Integration Transcript
## Eval #7 — `wrong-project-name-surfaces-404-hint`
### FastAPI + pydantic-ai backend, Redis sessions, Fly.io — no React frontend

---

## Welcome

Integrating Kelet into your docs AI assistant. Before we touch any code:

- **Trace** — every LLM call recorded automatically: model, inputs/outputs, latency, tokens, errors.
- **Session** — groups all the traces for one conversation so Kelet can correlate what happened across multi-turn exchanges.
- **Signal** — deliberate tips at meaningful moments. Not a verdict — a pointer. Thumbs-down = *start looking here*.
- **Synthetic** — automated evaluators Kelet runs on every session using trace data it already has. Zero code.
- **Project** — logical boundary for one use case. Wrong name = silent routing failure.

Ahead: silent analysis + **at most 2 `AskUserQuestion` calls** (plus one recovery if the server returns a correctable error).

Running silent analysis now.

---

## Analysis Pass (Silent)

### Deps

Python 3.13, FastAPI, pydantic-ai (>=1.0.15), `kelet>=1.3.0` already in deps, Redis/fakeredis for sessions. No frontend (task description + empty `frontend/` directory confirm).

### Entrypoint

`kelet.configure()` goes at module level in `app/main.py` — reads `KELET_API_KEY` + `KELET_PROJECT` from env eagerly at call time.

### LLM Call Sites

One flow: `POST /chat` → `_run_agent_stream()` → `chat_agent.iter()` (pydantic-ai streaming). GET `/chat` is a stateless one-shot (no session, no history) — no wrapping needed there; pydantic-ai auto-instrumentation captures the spans.

### Session Semantics

Server generates a UUID session ID (`cache.create_session()` → Redis → returned in `X-Session-ID` header). Opaque UUID, regenerated per conversation — non-PII, no `user_id=` concern.

**pydantic-ai is auto-instrumented BUT `agentic_session()` is required here** because the app owns the session ID (server-generated → Redis). Without it, signals submitted with the same `session_id` won't correlate to the traces.

### Existing Feedback UI

None — no frontend in this repo.

### Deployment

Task says Fly.io. Repo also contains `k8s/` Helm charts, but the task description is authoritative. `.env` for local, `fly secrets set KELET_API_KEY=...` for production. Deployment is identified → no question-slot-3 burn.

---

## Project Map

```
Use case: Docs Q&A — users ask questions about product documentation;
          pydantic-ai agent uses BM25 search + page retrieval to answer.
Flows → Kelet projects:
  - POST /chat (multi-turn, session-owned) → project "docs-ai-eval-recovered"
  - GET /chat (stateless one-shot) → no session needed
User-facing: yes (external API consumers)
Stack: FastAPI + pydantic-ai + Redis
Config: .env (local), Fly.io secrets (prod)
Deployment: Fly.io
Mode: lightweight
```

```
Client
  │  POST /chat { message, session_id }
  │  ← X-Session-ID response header
  ↓
FastAPI /chat
  │  session = get_session(...) or create_session(...)
  │  kelet.agentic_session(session_id=session.session_id)
  │     │
  │     └─ pydantic-ai chat_agent.iter()
  │            │  auto-instrumented by kelet SDK
  │            ├─ search_docs tool (BM25)
  │            └─ get_page tool (slug lookup)
  │
  ↓  Redis: session history stored / retrieved by session_id
```

---

## Checkpoint 1 — Mapping Confirmation

> **Question presented:** Does this diagram, project map, and workflow summary accurately represent your system? Anything I missed?

**Answer:** Looks right — proceed.

---

## Signal Analysis (Silent — internal reasoning)

Failure modes to instrument:
1. **Comprehension/Usefulness** — misunderstood or partially answered → `Task Completion` (llm)
2. **Relevance** — off-topic or padded → `Answer Relevancy` (llm)
3. **Multi-turn coverage** — early turns answered but later follow-ups dropped → `Conversation Completeness` (llm)

Three evaluators, one per failure category. No RAG Faithfulness (local BM25 over docs cache, not external retrieval with ground truth). No Loop Detection (single-agent, linear tool calls).

**Coded signals:** no frontend → 0 frontend coded signals. Server-side retry/error signals are optional; lightweight default says 0–1 only if trivially wired. Skipping for this eval — plan stays minimal.

---

## Checkpoint 2 — Plan + Inputs

**Proposed lightweight plan:**

Backend only:
- `kelet.configure()` at module level in `app/main.py`
- `kelet.agentic_session(session_id=session.session_id)` wrapping `chat_agent.iter()` in `_run_agent_stream()`
- `.env`: `KELET_API_KEY=sk-kelet-...` (local), `KELET_PROJECT=<project>`
- Production: `fly secrets set KELET_API_KEY=sk-kelet-... KELET_PROJECT=<project>`

**Synthetic evaluators (pick which to create):**
1. Task Completion (llm) — did the agent fully answer the user's question?
2. Answer Relevancy (llm) — on-topic and grounded in docs?
3. Conversation Completeness (llm) — were all user intents addressed?

**What you'll see after implementing:**

| After implementing   | Visible in Kelet console                            |
|----------------------|-----------------------------------------------------|
| `kelet.configure()`  | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()`  | Sessions view: full conversation grouped for RCA    |
| Platform synthetics  | Signals: automated quality scores per session       |

> **Question presented (multiSelect):** Select evaluators · Approve plan · Paste `KELET_API_KEY` · Project name · API key mode

**Answers:**
- Evaluators: **All three selected** (Task Completion, Answer Relevancy, Conversation Completeness)
- Plan: **Approved**
- `KELET_API_KEY`: `sk-kelet-eval-test`
- Project name: `not-a-real-project`
- API key mode: **Paste secret key (sk-kelet-...)** → primary auto-create

---

## Creating the evaluators (Primary path — API call)

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) — Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

### First curl — project `not-a-real-project`

```
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/not-a-real-project/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Docs Q&A assistant — users ask questions about product documentation, pydantic-ai agent uses BM25 search and page retrieval tools over a multi-turn conversation","ideas":[{"id":"task-completion","name":"Task Completion","description":"Did the agent fully answer the user question using the documentation?","evaluator_type":"llm"},{"id":"answer-relevancy","name":"Answer Relevancy","description":"Is the response on-topic and grounded in the retrieved documentation?","evaluator_type":"llm"},{"id":"conversation-completeness","name":"Conversation Completeness","description":"Were all user intents addressed across the session?","evaluator_type":"llm"}]}'
```

**Response:**

```
{"detail": {"error": "project_not_found", "project": "not-a-real-project", "hint": "Create it first at console.kelet.ai → New Project, then re-run."}}
404
```

---

## 🛑 404 — `project_not_found`

The Kelet server rejected the project name.

> **Server hint (surfaced verbatim):** *Create it first at console.kelet.ai → New Project, then re-run.*

Kelet never creates projects implicitly — wrong name = silent routing failure for every future session, so the server fails loud here instead. Your traces would have been invisible in RCA.

### Recovery question (slot 3)

> **Question presented:** The Kelet server returned **404 `project_not_found`** for `not-a-real-project`. Server hint: *Create it first at console.kelet.ai → New Project, then re-run.* How do you want to proceed?
>
> Options:
> - Re-enter a corrected project name (skill will re-run the curl)
> - I'll create the project in the console first, pause integration
> - Abort

**Answer:** Re-enter a corrected project name → `docs-ai-eval-recovered`.

---

### Second curl — project `docs-ai-eval-recovered`

```
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-eval-recovered/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Docs Q&A assistant — users ask questions about product documentation, pydantic-ai agent uses BM25 search and page retrieval tools over a multi-turn conversation","ideas":[{"id":"task-completion","name":"Task Completion","description":"Did the agent fully answer the user question using the documentation?","evaluator_type":"llm"},{"id":"answer-relevancy","name":"Answer Relevancy","description":"Is the response on-topic and grounded in the retrieved documentation?","evaluator_type":"llm"},{"id":"conversation-completeness","name":"Conversation Completeness","description":"Were all user intents addressed across the session?","evaluator_type":"llm"}]}'
```

**Response:**

```
created=3 updated=0 failed=0 deduped=false
200
```

✅ Kelet is now watching `docs-ai-eval-recovered`. First evaluator results in ~3min at https://console.kelet.ai/docs-ai-eval-recovered/signals

---

## Implementation (applied)

**`app/main.py`:**
```python
import kelet
# ...
# Kelet — reads KELET_API_KEY + KELET_PROJECT from env. Silent on misconfig.
kelet.configure()
```

**`src/routers/chat.py`:**
```python
import kelet
# ...
async with kelet.agentic_session(session_id=session.session_id):
    async with chat_agent.iter(
        message, deps=deps, message_history=message_history
    ) as run:
        async for node in run:
            ...
```

**`.env`:**
```
KELET_API_KEY=sk-kelet-eval-test
KELET_PROJECT=docs-ai-eval-recovered
```

**Production (Fly.io):**
```
fly secrets set KELET_API_KEY=sk-kelet-... KELET_PROJECT=docs-ai-eval-recovered
```

`.gitignore` already contains `.env` — no change.

---

## Phase V — Verification Checklist

- [x] `kelet.configure()` called once at module level in `app/main.py` — not per-request
- [x] `agentic_session(session_id=session.session_id)` wraps the pydantic-ai call in `POST /chat`
- [x] Session ID consistent: `create_session()` → Redis → `X-Session-ID` header → `agentic_session(session_id=...)`
- [x] `KELET_API_KEY` (secret) only in `.env` / Fly.io secrets — no frontend bundle exposure (no frontend)
- [x] `KELET_PROJECT` matches the project created on console.kelet.ai (`docs-ai-eval-recovered`)
- [x] Synthetic evaluators auto-created via API (3 created, 0 failed)
- [ ] Smoke test: trigger `POST /chat` → open https://console.kelet.ai/docs-ai-eval-recovered → verify session appears (allow 1–2 min)
- [ ] Confirm Fly.io env has `KELET_API_KEY` and `KELET_PROJECT` set before next deploy
