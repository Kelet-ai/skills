# Kelet Integration — docs-ai (eval #7, wrong-project-name-surfaces-404-hint)

Developer prompt: "integrate kelet into my app"

App context (pre-attached): FastAPI backend using pydantic-ai. Sessions in Redis. No React.
Deployed on Fly.io. The developer will give `not-a-real-project` at Checkpoint 2 and paste
`sk-kelet-eval-test` — then correct to `docs-ai-iter8-recovered` at the recovery prompt.

---

## Phase 0 — Welcome

Rendered the welcome banner verbatim:

> 🕵️  Welcome to Kelet — your AI detective

Core concepts (detective metaphor, concept before mechanics):

- **Trace = the scene.** Every LLM call + tool use auto-recorded after `kelet.configure()`.
- **Signal = the tip.** 👎, edit, abandon — points the detective at something worth investigating.
- **Synthetic = forensic tools.** Automated signals from trace data. No code.
- **Session = the case file.** Traces grouped by one unit of work.
- **Project = the jurisdiction.** One per agentic use case. Wrong project = invisible in RCA.

The trigger message already described the app → no pre-flight question.

Progress tracker:

```
📍  Mapping 🔄 → Signals ○ → Plan ○ → Implement ○ → Verify ○
```

---

## Phase 1 — MAPPING (silent analysis)

> 🔎  MAPPING

Silent read of `pyproject.toml`, `app/main.py`, `src/routers/chat.py`, `src/agent/__init__.py`,
`src/cache/`, `src/settings/__init__.py`, `.env`, `.env.example`, `.gitignore`, `k8s/`,
`.github/workflows/`.

Findings:

- **Stack:** FastAPI + pydantic-ai (auto-instrumented). pydantic-settings for config.
- **Entrypoint:** `app/main.py` `asynccontextmanager lifespan` — clean slot for
  `kelet.configure()` and a `finally:` `kelet.shutdown()`.
- **LLM call sites:** two — `POST /chat` (SSE, session-scoped) and `GET /chat` (stateless
  one-shot). Both call `chat_agent.iter(...)`.
- **Session tracking:** `ChatSession.session_id` = UUID generated in `cache.create_session`,
  persisted in Redis, **returned via `X-Session-ID` response header** (already
  `expose_headers`'d for CORS). New conversation → new UUID. Correct Kelet session ID — no mismatch.
- **Stable PII user identifier:** none in scope (no phone/email). `user_id=` omitted silently.
- **User-facing UI:** no React/frontend components to wire — server-only. No existing thumbs /
  edit / copy hooks.
- **Deployment:** authoritative app description says Fly.io. Repo also ships `k8s/charts/` +
  `k8s/environments/prod.yaml` + `stag.yaml`, so multi-env is real — surface in Checkpoint 1.
- **Project name:** not yet defined — ask at Checkpoint 2.

### Project Map

```
Use case: Kelet docs AI assistant — RAG Q&A over documentation
Flows → Kelet projects:
  - flow "docs Q&A" → project "<to-confirm>" (single flow)
User-facing: yes (chat UI consumes POST /chat SSE + reads X-Session-ID)
Stack: FastAPI + pydantic-ai (auto-instrumented)
Config: .env + pydantic-settings (env_file=".env") — configure() needs explicit args
Deployment: Fly.io (per app description); k8s/helmfile also present (prod + stag overlays)
Mode: lightweight (just configure + agentic_session + managed synthetics; no coded signals)
```

### Architecture (ASCII)

```
 Browser
    │  POST /chat { message, session_id? }
    ▼
 FastAPI   ── rate limiter ──┐
    │                        │
    │  session_id = Redis UUID (create_session or get_session)
    │  ──► X-Session-ID response header (CORS expose_headers)
    │
    ▼
 agentic_session(session_id=session.session_id)   ◄── wraps the run
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

Presented diagram + project map. Session semantics unambiguous (UUID per conversation,
regenerates on reset) → no need to burn a slot on session ID. Multi-env detected in
`k8s/environments/` — folded into the same question.

**Question:** "Does this diagram, map, and workflow summary accurately represent your system?
If you ship to multiple envs (prod + stag), do you want one Kelet project across envs, or
one per env?"

**Simulated answer:** "Yes, looks right." → accept the map, single project for now.

```
📍  Mapping ✅ → Signals 🔄 → Plan ○ → Implement ○ → Verify ○
```

---

## Phase 2 — SIGNALS (silent reasoning)

> 🔎  SIGNALS

Internal reasoning only — not surfaced to the developer until Checkpoint 2.

- **Synthetic anchor:** `Task Completion` — universal "did the agent answer the user's goal?"
- **Synthetic #2:** `Conversation Completeness` — multi-turn chat in Redis, users will ask
  follow-ups. Catches deflected/unaddressed intents across turns.
- **Synthetic #3:** `RAG Faithfulness` — agent has real retrieval (`search_docs` BM25 tool +
  `get_page`). Scores claims against retrieved docs → catches doc-grounded hallucinations.
- **Coded signals:** zero. No UI hooks in this repo; adding speculative code contradicts
  lightweight mode.

Rephrase detection deliberately NOT shipped as coded — correct layer is an LLM synthetic
scoring the preceding turn. Text-match heuristics miss real rephrase and fire on innocent
clarifications.

---

## Phase 3 — PLAN + Checkpoint 2 (AskUserQuestion #2)

> 🗺️  PLAN

Lightweight plan:

1. Add `kelet>=1.0` to `pyproject.toml`.
2. Add `kelet_api_key` + `kelet_project` to `Settings` (pydantic-settings → explicit args required).
3. In `app/main.py` lifespan: `kelet.configure(api_key=..., project=...)` gated on `kelet_api_key`;
   `kelet.shutdown()` in the `finally:` so BatchSpanProcessor flushes on SIGTERM / pod rotation.
4. In `src/routers/chat.py`: wrap `chat_agent.iter(...)` in `kelet.agentic_session(session_id=...)`
   — Redis session_id for `POST /chat`, one-shot UUID for `GET /chat`.
5. Write `KELET_API_KEY` + `KELET_PROJECT` to `.env` (already `.gitignore`'d). For Fly.io prod:
   `fly secrets set KELET_API_KEY=sk-kelet-... KELET_PROJECT=<project>`.
6. Auto-create synthetic evaluators via `POST /api/projects/<project>/synthetics`.

### "What you'll see" table

| After implementing         | Visible in Kelet console                                        |
| -------------------------- | --------------------------------------------------------------- |
| `kelet.configure()`        | LLM spans in Traces: model, tokens, latency, errors             |
| `agentic_session()`        | Sessions view: full conversation grouped for RCA                |
| Platform synthetics        | Signals: Task Completion / Conversation Completeness / Faithfulness scores |

**Single AskUserQuestion (multiSelect)** bundling synthetic picks + plan approval + keys/project
+ key mode:

- Proposed synthetic evaluators (multiSelect): Task Completion · Conversation Completeness ·
  RAG Faithfulness · None
- Plan approval: Does the rest of the plan look right?
- `KELET_API_KEY` (sk-kelet-...) — needed for auto-create. Get at console.kelet.ai/api-keys.
- Project name — must exist at console.kelet.ai first (wrong name = 404 with hint).
- API key mode: Paste secret key / I'll grab one / I can't paste secrets.

**Simulated answer:**

- Synthetics: **all three** (Task Completion, Conversation Completeness, RAG Faithfulness).
- Plan approved.
- Project name: **`not-a-real-project`** (deliberately invalid per eval spec).
- API key mode: **Paste secret key** → `sk-kelet-eval-test`.

```
📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement 🔄 → Verify ○
```

---

## Phase 4 — IMPLEMENT

> 🛠️  IMPLEMENT

(Skipping ExitPlanMode per eval override — continued directly.)

### Code edits

- **`app/main.py`** — `import kelet`; `kelet.configure(...)` in lifespan gated on `kelet_api_key`;
  `kelet.shutdown()` in the `finally:` block after `await redis.aclose()`.
- **`src/routers/chat.py`** — wrap both agent call sites. `POST /chat` uses the Redis
  `session.session_id`; `GET /chat` uses a per-request `str(uuid.uuid4())` (stateless
  one-shot = its own case file).
- **`src/settings/__init__.py`** — added `kelet_api_key: str = ""` and `kelet_project: str = ""`.
- **`pyproject.toml`** — added `"kelet>=1.0"` to `dependencies`.
- **`.env`** — set `KELET_API_KEY=sk-kelet-eval-test` + `KELET_PROJECT=docs-ai-iter8-recovered`
  (post-recovery value). `.env` is already gitignored.

### Synthetic creation — attempt 1 (project = `not-a-real-project`)

Printed verbatim before the curl:

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) —
> Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

**Curl invocation #1 (verbatim):**

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/not-a-real-project/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Kelet docs AI assistant — RAG Q&A over documentation with pydantic-ai agent, BM25 retrieval, multi-turn chat sessions in Redis","ideas":[{"id":"task_completion","name":"Task Completion","description":"Did the agent accomplish the user'"'"'s goal of answering their documentation question with accurate, complete information?","evaluator_type":"llm"},{"id":"conversation_completeness","name":"Conversation Completeness","description":"Were the user'"'"'s intentions fully addressed across the multi-turn session, or did the agent leave questions deflected or unanswered?","evaluator_type":"llm"},{"id":"rag_faithfulness","name":"RAG Faithfulness","description":"Do the agent'"'"'s claims stay faithful to the content retrieved from the BM25 docs search tool? Flag hallucinations or contradictions with the source docs.","evaluator_type":"llm","context":"The agent has a search_docs tool (BM25) and get_page tool returning doc content. Faithfulness is judged against the retrieved doc pages."}]}'
```

(URL substituted to `http://localhost:8765/...` per eval environment override — the real
`https://api.kelet.ai/...` endpoint is what the skill normally hits.)

**Response body (verbatim):**

```
{"detail": {"error": "project_not_found", "project": "not-a-real-project", "hint": "Create it first at console.kelet.ai → New Project, then re-run."}}
404
```

### 🚨 404 detected — `project_not_found`

Parsed the response: status `404`, `detail.error = "project_not_found"`,
`detail.project = "not-a-real-project"`, `detail.hint = "Create it first at
console.kelet.ai → New Project, then re-run."`.

Surfaced the hint to the developer **verbatim** — not paraphrased:

> ❌ Kelet returned **404 project_not_found** for `not-a-real-project`.
>
> Server hint: *"Create it first at console.kelet.ai → New Project, then re-run."*
>
> Wrong project name = silent routing failure once traces start flowing — and synthetic
> evaluator creation can't attach to a project that doesn't exist. Stopping here so we don't
> ship a broken setup.

## Recovery (AskUserQuestion #3)

**Question:** "The project `not-a-real-project` doesn't exist in your Kelet workspace.
What do you want to do?"

**Options:**

- "Re-enter a corrected project name" — you already created one at the console.
- "Halt — I need to create the project first" — go to console.kelet.ai, create the project,
  then re-run this skill.
- "Try a different project name from memory" — skill will re-run the curl with the new name.

**Simulated answer:** *Re-enter a corrected project name* → **`docs-ai-iter8-recovered`**.

Updated `.env` → `KELET_PROJECT=docs-ai-iter8-recovered`.

### Synthetic creation — attempt 2 (project = `docs-ai-iter8-recovered`)

Re-ran the same curl with the corrected project name — no developer confirmation re-prompt,
no question burned; the recovery question already captured intent.

**Curl invocation #2 (verbatim):**

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-iter8-recovered/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Kelet docs AI assistant — RAG Q&A over documentation with pydantic-ai agent, BM25 retrieval, multi-turn chat sessions in Redis","ideas":[{"id":"task_completion","name":"Task Completion","description":"Did the agent accomplish the user'"'"'s goal of answering their documentation question with accurate, complete information?","evaluator_type":"llm"},{"id":"conversation_completeness","name":"Conversation Completeness","description":"Were the user'"'"'s intentions fully addressed across the multi-turn session, or did the agent leave questions deflected or unanswered?","evaluator_type":"llm"},{"id":"rag_faithfulness","name":"RAG Faithfulness","description":"Do the agent'"'"'s claims stay faithful to the content retrieved from the BM25 docs search tool? Flag hallucinations or contradictions with the source docs.","evaluator_type":"llm","context":"The agent has a search_docs tool (BM25) and get_page tool returning doc content. Faithfulness is judged against the retrieved doc pages."}]}'
```

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
- `kelet.shutdown()` called in lifespan `finally:` block — BatchSpanProcessor will flush on
  SIGTERM / Fly.io pod rotation.
- Secret key server-only (`.env`, never in a frontend bundle; no React here).
- `.env` gitignored (pre-existing rule).
- Project name now correct (`docs-ai-iter8-recovered`) in `.env` and in the synthetic creation response.
- For Fly.io prod: `fly secrets set KELET_API_KEY=sk-kelet-eval-test KELET_PROJECT=docs-ai-iter8-recovered`.
- Smoke test: trigger a chat POST → open `https://console.kelet.ai/docs-ai-iter8-recovered`
  → a session should appear in the Sessions view within a couple of minutes. First synthetic
  scores arrive in ~3 minutes (`Signals` tab).

### ✅ Success banner

> ✅ Created 3 evaluators in docs-ai-iter8-recovered: Task Completion, Conversation Completeness,
> RAG Faithfulness. First results in ~3min at https://console.kelet.ai/docs-ai-iter8-recovered/signals

```
📍  Mapping ✅ → Signals ✅ → Plan ✅ → Implement ✅ → Verify ✅
```

Integration complete. Three `AskUserQuestion` calls total (at the budget ceiling; the third
was the 404 recovery prompt, not a pre-planned slot — well spent).
