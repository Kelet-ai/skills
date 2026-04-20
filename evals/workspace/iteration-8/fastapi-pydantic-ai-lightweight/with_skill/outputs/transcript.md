# Kelet Integration — docs-ai (eval #1, lightweight)

Developer prompt: "integrate kelet into my app"

App context (pre-attached): FastAPI backend using pydantic-ai. Sessions stored in Redis
(session_id generated server-side, returned in X-Session-ID response header). No React
frontend — plain HTML. Deployed on Fly.io.

---

## Phase 0 — Welcome

Rendered the welcome banner verbatim:

> 🕵️  Welcome to Kelet — your AI detective

Taught the core concepts before touching any code:

- **Trace = the scene.** Every LLM call + tool use auto-recorded after `kelet.configure()`.
- **Signal = the tip.** 👎, edit, abandon — points the detective at something worth investigating.
- **Synthetic = forensic tools.** Automated signals from trace data. No code.
- **Session = the case file.** Traces grouped by one unit of work.
- **Project = the jurisdiction.** One per agentic use case. Wrong project = invisible in RCA.

No pre-flight question needed — the trigger message already described the app.

Progress tracker shown:

```
📍  Mapping 🔄 → Signals ○ → Plan ○ → Implement ○ → Verify ○
```

---

## Phase 1 — MAPPING (silent analysis)

> 🔎  MAPPING

Silent read of `pyproject.toml`, `app/main.py`, `src/routers/chat.py`, `src/agent/__init__.py`,
`src/cache/__init__.py`, `src/settings/__init__.py`, `.env`, `.env.example`, `.gitignore`,
`frontend/.env`, `k8s/`, `.github/workflows/`.

Findings:

- **Stack:** FastAPI + pydantic-ai (auto-instrumented). pydantic-settings for config.
- **Entrypoint:** `app/main.py` with an `asynccontextmanager` lifespan — ideal spot for
  `kelet.configure()` and the `finally:` block for `kelet.shutdown()`.
- **LLM call sites:** two — `POST /chat` (SSE, session-scoped) and `GET /chat` (stateless
  one-shot). Both call `chat_agent.iter(...)`.
- **Session tracking:** `ChatSession.session_id` = UUID generated in `cache.create_session`,
  persisted in Redis, **returned via `X-Session-ID` response header** (already `expose_headers`'d
  for CORS). Resets = new UUID. This is the correct Kelet session ID — no mismatch.
- **No stable PII user identifier in scope** (no phone/email) — `user_id=` omitted. No prompt needed.
- **User-facing UI:** none in this repo — plain HTML frontend not present here. No thumbs / edit / copy hooks to wire.
- **Deployment:** repo contains `k8s/charts/` + `helmfile.yaml.gotmpl` with `environments/prod.yaml` + `stag.yaml`,
  but the authoritative app description says Fly.io. Treated as Fly.io per the developer. Multi-env is a real
  possibility (stag + prod), worth confirming in the mapping question.
- **Project name:** not yet present in a consistent form — ask at Checkpoint 2.

### Project Map

```
Use case: Kelet docs AI assistant — RAG Q&A over documentation
Flows → Kelet projects:
  - flow "docs Q&A" → project "docs-ai-iter8" (single flow)
User-facing: yes (chat UI consumes POST /chat SSE + reads X-Session-ID)
Stack: FastAPI + pydantic-ai (auto-instrumented)
Config: .env + pydantic-settings (env_file=".env") — configure() needs explicit args
Deployment: Fly.io (per app description); k8s/helmfile also present (prod + stag overlays)
Mode: lightweight (just configure + agentic_session + managed synthetics; no coded signals)
```

### Architecture (ASCII)

```
 Browser (plain HTML)
    │  POST /chat { message, session_id? }
    ▼
 FastAPI   ── rate limiter ──┐
    │                        │
    │  session_id = Redis UUID (create_session or get_session)
    │  ──► X-Session-ID response header (CORS expose_headers)
    │
    ▼
 agentic_session(session_id=session.session_id)   ◄── this wraps the run
    │
    ▼
 chat_agent.iter(message, deps, message_history)    (pydantic-ai auto-instrumented)
    │
    ▼  LLM call spans auto-captured → Kelet trace exporter
    │
 SSE chunks ◄──────── yield data: {chunk}
    │
 session.history persisted → Redis (TTL 30m)
```

## Checkpoint 1 — MAPPING confirmation (AskUserQuestion #1)

Presented diagram + project map. Session semantics are unambiguous (UUID per conversation,
regenerates on reset / expiry) → no need to burn an extra slot on session ID. Multi-env was
detected (k8s has prod + stag overlays even though the developer said Fly.io) — folded into
the same question.

**Question:** "Does this diagram, map, and workflow summary accurately represent your system?
If you ship to multiple envs (prod + stag), do you want one Kelet project across envs, or one per env?"

**Simulated answer:** "Yes, looks right." → accept the map, single project `docs-ai-iter8` for now.

```
📍  Mapping ✅ → Signals 🔄 → Plan ○ → Implement ○ → Verify ○
```

---

## Phase 2 — SIGNALS (silent reasoning)

> 🔎  SIGNALS

Silent internal reasoning — not shown to the developer. Summary:

- **Synthetic anchor:** `Task Completion` — universal "did the agent answer the user's question?"
- **Synthetic #2:** `Conversation Completeness` — multi-turn chat in Redis, users will ask
  follow-ups. Catches deflected/unaddressed intents across turns.
- **Synthetic #3:** `RAG Faithfulness` — agent has real retrieval (`search_docs` BM25 tool +
  `get_page`). Faithfulness scores claims against the retrieved pages → catches doc-grounded
  hallucinations. Distinct category from Task Completion.
- **Coded signals:** zero. No existing UI hooks in this repo to wire to; adding speculative
  code would contradict lightweight mode.

Diagnostic coverage: Comprehension/Usefulness (Task Completion) + User reaction /
multi-turn intent (Conversation Completeness) + Correctness (RAG Faithfulness). Three
distinct failure categories, no overlap.

Rephrase detection deliberately **not** shipped as a coded signal — right layer is an LLM
synthetic scoring the preceding turn; text-match heuristics both miss real rephrase and fire
on innocent clarifications.

---

## Phase 3 — PLAN + Checkpoint 2 (AskUserQuestion #2)

> 🗺️  PLAN

Presented the lightweight plan:

1. Add `kelet>=1.0` to `pyproject.toml`.
2. Add `kelet_api_key` + `kelet_project` fields to `Settings` (pydantic-settings requires explicit args).
3. In `app/main.py` lifespan: call `kelet.configure(api_key=..., project=...)` gated on `kelet_api_key`;
   call `kelet.shutdown()` in the `finally:` block so BatchSpanProcessor flushes on SIGTERM / pod rotation.
4. In `src/routers/chat.py`: wrap `chat_agent.iter(...)` in `kelet.agentic_session(session_id=...)` —
   Redis session_id for `POST /chat`, one-shot UUID for `GET /chat`.
5. Write `KELET_API_KEY` + `KELET_PROJECT` to `.env` (already in `.gitignore`). For Fly.io prod:
   `fly secrets set KELET_API_KEY=sk-kelet-... KELET_PROJECT=docs-ai-iter8`.
6. Auto-create synthetic evaluators in the chosen project via `POST /api/projects/<project>/synthetics`.

### "What you'll see" table

| After implementing         | Visible in Kelet console                                        |
| -------------------------- | --------------------------------------------------------------- |
| `kelet.configure()`        | LLM spans in Traces: model, tokens, latency, errors             |
| `agentic_session()`        | Sessions view: full conversation grouped for RCA                |
| Platform synthetics        | Signals: Task Completion / Conversation Completeness / Faithfulness scores |

**Single AskUserQuestion (multiSelect)** bundling synthetic picks + plan approval + keys/project + key mode:

- **Proposed synthetic evaluators (multiSelect):** Task Completion · Conversation Completeness · RAG Faithfulness · None
- **Plan approval:** Does the rest of the plan look right?
- **KELET_API_KEY (sk-kelet-...)** — needed for synthetic auto-create. Get at console.kelet.ai/api-keys.
- **Project name** — must exist at console.kelet.ai first (wrong name = silent routing / 404 hint).
- **API key mode:** Paste secret key / I'll grab one / I can't paste secrets.

**Simulated answer:**

- Synthetics: ALL THREE (Task Completion, Conversation Completeness, RAG Faithfulness).
- Plan approved.
- Project name: `docs-ai-iter8` (already created at the console).
- API key mode: **Paste secret key** → `sk-kelet-eval-test`.

```
📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement 🔄 → Verify ○
```

---

## Phase 4 — IMPLEMENT

> 🛠️  IMPLEMENT

(Skipping ExitPlanMode per eval override — continued directly.)

### Code edits

**`app/main.py`** — import kelet; configure() in lifespan gated on api_key; shutdown() in finally.

```python
import kelet
...
@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.kelet_api_key:
        kelet.configure(
            api_key=settings.kelet_api_key,
            project=settings.kelet_project,
        )
    ...
    try:
        yield
    finally:
        await docs_cache.stop()
        await redis.aclose()
        kelet.shutdown()
```

**`src/routers/chat.py`** — wrap both agent call sites. `POST /chat` uses the Redis
session_id; `GET /chat` uses a per-request UUID (stateless = its own case file).

```python
async with kelet.agentic_session(session_id=session.session_id), chat_agent.iter(
    message, deps=deps, message_history=message_history
) as run:
    ...

# stateless
stateless_session_id = str(uuid.uuid4())
async with kelet.agentic_session(session_id=stateless_session_id), chat_agent.iter(q, deps=deps) as run:
    ...
```

**`src/settings/__init__.py`** — added `kelet_api_key: str = ""` and `kelet_project: str = ""`.

**`pyproject.toml`** — added `"kelet>=1.0"` to `dependencies`.

**`.env`** — set `KELET_API_KEY=sk-kelet-eval-test` + `KELET_PROJECT=docs-ai-iter8`. `.env`
is already gitignored.

### Synthetic creation (auto via API)

Printed verbatim before the curl:

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) —
> Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

**Curl invocation (verbatim):**

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-iter8/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Kelet docs AI assistant — RAG Q&A over documentation with pydantic-ai agent, BM25 retrieval, multi-turn chat sessions in Redis","ideas":[{"id":"task_completion","name":"Task Completion","description":"Did the agent accomplish the user'"'"'s goal of answering their documentation question with accurate, complete information?","evaluator_type":"llm"},{"id":"conversation_completeness","name":"Conversation Completeness","description":"Were the user'"'"'s intentions fully addressed across the multi-turn session, or did the agent leave questions deflected or unanswered?","evaluator_type":"llm"},{"id":"rag_faithfulness","name":"RAG Faithfulness","description":"Do the agent'"'"'s claims stay faithful to the content retrieved from the BM25 docs search tool? Flag hallucinations or contradictions with the source docs.","evaluator_type":"llm","context":"The agent has a search_docs tool (BM25) and get_page tool returning doc content. Faithfulness is judged against the retrieved doc pages."}]}'
```

(URL substituted to `http://localhost:8765/...` per eval environment override — the real
`https://api.kelet.ai/...` endpoint is what the skill normally hits.)

**Response body (verbatim):**

```
created=3 updated=0 failed=0 deduped=false
200
```

Success. `failed=0` — no retries needed.

---

## Phase 5 — VERIFY

> 🕵️  VERIFY

- Every agentic entry point covered: `POST /chat` ✓ and `GET /chat` ✓ both wrapped in `agentic_session()`.
- Session ID consistent end-to-end: client → Redis UUID → `X-Session-ID` header → `agentic_session(session_id=...)`.
- `configure()` called once at startup (lifespan), not per-request.
- `kelet.shutdown()` called in lifespan `finally:` block — BatchSpanProcessor will flush on SIGTERM / Fly.io pod rotation.
- Secret key server-only (`.env`, never in a frontend bundle; no React here).
- `.env` gitignored (pre-existing rule).
- For Fly.io prod: `fly secrets set KELET_API_KEY=sk-kelet-eval-test KELET_PROJECT=docs-ai-iter8`.
- Smoke test: trigger a chat POST → open `https://console.kelet.ai/docs-ai-iter8` → a session
  should appear in the Sessions view within a couple of minutes. First synthetic scores
  arrive in ~3 minutes (`Signals` tab).

### ✅ Success banner

> ✅ Created 3 evaluators in docs-ai-iter8: Task Completion, Conversation Completeness,
> RAG Faithfulness. First results in ~3min at https://console.kelet.ai/docs-ai-iter8/signals

```
📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement ✅ → Verify ✅
```

Integration complete. Two AskUserQuestion calls total (within the ideal budget).
