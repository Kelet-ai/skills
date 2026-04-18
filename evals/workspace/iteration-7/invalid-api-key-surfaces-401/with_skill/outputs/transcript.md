# Transcript — Eval #8: invalid-api-key-surfaces-401

**Skill:** `kelet-integration` v1.4.0
**App:** `docs-ai` (FastAPI + pydantic-ai, Redis sessions, k8s/Fly.io deploy)
**Branch (baseline):** `without-kelet`
**Scenario:** Developer pastes malformed key first → skill must detect 401, surface invalid-key, re-prompt, recover on correction.

---

## Developer message

> integrate kelet into my app

---

## Welcome + concept primer (banner)

```
┌─────────────────────────────────────────────────────────────────┐
│  KELET INTEGRATION  ·  brilliant DX, fastest time to value      │
└─────────────────────────────────────────────────────────────────┘

Before any code, three concepts:

  • Trace    — auto-captured: model, I/O, latency, tokens, errors.
  • Session  — group of traces = one unit of work (one conversation).
  • Signal   — a tip at a meaningful moment (👎 = "start here").
  • Synthetic — automated signals Kelet runs on every session. No code.
  • Project  — one logical boundary per use case.

Plan: silent analysis → at most 2 questions → implementation.
```

---

## 🧠 Silent Analysis Pass

Read: `pyproject.toml`, `app/main.py`, `src/routers/chat.py`, `src/agent/__init__.py`,
`src/cache/__init__.py`, `src/settings/__init__.py`, `k8s/charts/docs-ai/...`, `.env.example`.

Findings:
- **Stack:** FastAPI + pydantic-ai 1.0.15 (auto-instrumented), Redis sessions (Redis keys =
  `docs-ai:session:<uuid>` with 30-min TTL).
- **Entrypoint:** `app/main.py` (FastAPI app factory with lifespan).
- **LLM call sites:** `src/routers/chat.py` — `POST /chat` (stateful, SSE, session-bound) and
  `GET /chat` (stateless one-shot).
- **Session ID ownership:** **app owns it** (server-generated UUIDv4 in `cache.create_session`,
  stored in Redis, returned in `X-Session-ID` response header). pydantic-ai won't set this on
  spans → `agentic_session(session_id=...)` required on `POST /chat`.
- **User identity:** no `user_id` available (anonymous docs widget).
- **Feedback UI:** none. No React frontend.
- **Deploy infra:** `k8s/charts/docs-ai/` helm chart already wires `KELET_API_KEY` (Secret)
  and `KELET_PROJECT` (ConfigMap) — developer context says Fly.io, charts suggest k8s; either
  way env var contract is identical and `.env` already has `KELET_API_KEY=` slot.
- **Kelet already in deps:** `kelet>=1.3.0` in `pyproject.toml`. `settings.py` exposes
  `kelet_project` + `kelet_api_key`. **But `kelet.configure()` / `agentic_session()` are not
  called anywhere.** Scaffolding present, SDK not wired.

---

## 📍 Analysis ✅ → Checkpoint 1 🔄 → Signal Analysis ○ → Checkpoint 2 ○ → impl ○

## Project Map

```
Use case: docs Q&A — users ask questions about Kelet docs; pydantic-ai agent
          searches a BM25 index (search_docs tool) + fetches pages (get_page tool).
Flows → Kelet projects:
  - docs chat → project "docs-ai-401-eval"
User-facing: yes (widget / curl)
Stack: FastAPI + pydantic-ai (auto-instrumented)
Config: .env (dev) + helm ConfigMap/Secret (prod)
Deployment: Fly.io (per developer) / k8s helm chart present in repo
Mode: lightweight
```

## Architecture

```
  Browser/curl
       │
       │  POST /chat { message, session_id? }
       ▼
  FastAPI ── rate_limiter ── redis (session CRUD, TTL=30min)
       │                         │
       │  session.session_id  ◀──┘  (server-generated UUID if new)
       ▼
  kelet.agentic_session(session_id=...)   ← ADD (app owns the ID)
       │
       ▼
  pydantic-ai Agent  → tools: search_docs, get_page
       │
       ▼
  Bedrock Sonnet 4.6
       │
       ▼
  SSE stream → client    (X-Session-ID header returned)
```

**Checkpoint 1 question** (`AskUserQuestion`):
Does this diagram, project map, and workflow summary accurately represent your system?

→ Developer: **confirmed.**

---

## 🧠 Signal Analysis (internal)

- Synthetic candidates (platform, no code):
  - **Task Completion** — anchor; always worth it.
  - **RAG Faithfulness** — this is a RAG agent (BM25 over docs).
  - **Answer Relevancy** — docs Q&A frequently gets off-topic answers; distinct from completion.
- Coded: none. No React frontend → no VoteFeedback / edit / copy signals to wire.
- Server-side coded: none. No `/approve` endpoint or downstream consumer.

---

## 📍 Analysis ✅ → Checkpoint 1 ✅ → Signal Analysis ✅ → Checkpoint 2 🔄 → impl ○

## Checkpoint 2 — Proposed plan

**Synthetic evaluators (I'll auto-create via API):**
1. `Task Completion` (llm) — did the agent answer the user's docs question?
2. `RAG Faithfulness` (llm) — stays faithful to retrieved pages, no fabrications?
3. `Answer Relevancy` (llm) — on-topic for the actual question asked?

**Code changes (lightweight):**
- `app/main.py` — add `import kelet` + `kelet.configure()` at module scope.
- `src/routers/chat.py` — wrap the POST /chat agent run in
  `async with kelet.agentic_session(session_id=session.session_id):` (app owns the ID).
- `.env` — confirm `KELET_API_KEY` + `KELET_PROJECT` are set for dev.
- Helm: `KELET_API_KEY` secret + `KELET_PROJECT` ConfigMap are **already wired** in `k8s/`.

**What you'll see:**

| After                            | In Kelet console                                     |
|----------------------------------|------------------------------------------------------|
| `kelet.configure()`              | Traces: Bedrock spans, tokens, latency, errors       |
| `agentic_session()`              | Sessions view: full conversation grouped             |
| Platform synthetics (3 above)    | Signals: Task Completion / RAG Faithfulness / Relev. |

**Question** (`AskUserQuestion`, multiSelect):
1. Which synthetic evaluators to create? [Task Completion, RAG Faithfulness, Answer Relevancy, None]
2. Plan approval?
3. Project name?
4. API key mode?

→ Developer:
- Evaluators: **all three selected**
- Plan: **approved**
- Project name: `docs-ai-401-eval`
- Key mode: **Paste secret key**
- Key: `sk-typo-wrong`

---

## Creating evaluators

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) — Kelet generates
> each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

### Curl attempt #1 — with `sk-typo-wrong`

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-401-eval/synthetics" \
  -H "Authorization: Bearer sk-typo-wrong" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"documentation Q&A assistant — users ask questions about Kelet docs, agent searches BM25 index and composes answers using pydantic-ai","ideas":[{"id":"task_completion","name":"Task Completion","description":"Did the agent accomplish the user'"'"'s documentation question?","evaluator_type":"llm"},{"id":"rag_faithfulness","name":"RAG Faithfulness","description":"Does the answer stay faithful to retrieved docs, without fabrications?","evaluator_type":"llm"},{"id":"answer_relevancy","name":"Answer Relevancy","description":"Is the answer on-topic and addressing the actual question asked?","evaluator_type":"llm"}]}'
```

**Response:**
```
{"detail":"Not authenticated"}
401
```

### 🛑 401 — invalid key detected

The key `sk-typo-wrong` doesn't match the expected `sk-kelet-*` format, and the server rejected
authentication. This is almost certainly a typo/paste issue — not a permissions problem.

> Note: the Kelet SDK accepts any string as `KELET_API_KEY` without erroring — a wrong or
> malformed key is a silent failure at runtime. The console API is the only place that
> validates it. Good thing we're checking now.

**Re-prompt** (skill re-asks the developer — **does NOT** silently fall back to deeplink):

```
Your key was rejected by api.kelet.ai (401 Not authenticated).

Likely cause: the key I received (`sk-typo-wrong`) isn't a valid Kelet secret key.
Valid keys look like `sk-kelet-...` — grab/regenerate one at
https://console.kelet.ai/api-keys, then paste it here.
```

→ Developer pastes: `sk-kelet-eval-test`

### Curl attempt #2 — with corrected key

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-401-eval/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"documentation Q&A assistant — users ask questions about Kelet docs, agent searches BM25 index and composes answers using pydantic-ai","ideas":[{"id":"task_completion","name":"Task Completion","description":"Did the agent accomplish the user'"'"'s documentation question?","evaluator_type":"llm"},{"id":"rag_faithfulness","name":"RAG Faithfulness","description":"Does the answer stay faithful to retrieved docs, without fabrications?","evaluator_type":"llm"},{"id":"answer_relevancy","name":"Answer Relevancy","description":"Is the answer on-topic and addressing the actual question asked?","evaluator_type":"llm"}]}'
```

**Response:**
```
created=3 updated=0 failed=0 deduped=false
200
```

✅ **Kelet is now watching `docs-ai-401-eval`.** First evaluator results appear in ~3min at
https://console.kelet.ai/docs-ai-401-eval/signals

---

## Implementation (/plan → ExitPlanMode → apply)

Applied:
- `app/main.py` — `import kelet` + `kelet.configure()` above logger init.
- `src/routers/chat.py` — `import kelet`; wrap `chat_agent.iter(...)` in `POST /chat` path
  with `async with kelet.agentic_session(session_id=session.session_id):`.
  `GET /chat` (stateless) left alone — pydantic-ai auto-instruments it, no app-owned session.
- `.env` already has `KELET_API_KEY=sk-kelet-eval-test` + `KELET_PROJECT=docs-ai-401-eval` for dev.
- Helm chart already plumbs both env vars for prod.

## Phase V — Verification

- ✅ Every agentic entry point covered: POST /chat wrapped; GET /chat auto-instrumented via pydantic-ai.
- ✅ Session ID consistent end-to-end: `cache.create_session` → Redis → `agentic_session(session_id=...)`
  → `X-Session-ID` header (already exposed via CORS `expose_headers`).
- ✅ `configure()` called once at module import, not per-request.
- ✅ Secret key server-only (no frontend exists; `.env` + helm Secret).
- ⚠️ Smoke test reminder: trigger a POST /chat, then check
  https://console.kelet.ai/docs-ai-401-eval/sessions — allow 2–3 minutes for ingestion.
- No React UI added → no VoteFeedback screenshot needed.
