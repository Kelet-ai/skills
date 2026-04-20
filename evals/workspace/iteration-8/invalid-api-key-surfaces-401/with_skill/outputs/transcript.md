# Eval #8 — invalid-api-key-surfaces-401

## Phase flow

```
Mapping ✅ → Signals ✅ → Plan ✅ → Implement ✅ → Verify ✅
```

## Checkpoint 1 — MAPPING (AskUserQuestion #1)

Presented project map + ASCII diagram:

- Use case: Docs Q&A via pydantic-ai agent
- Flow -> project: `chat` -> `docs-ai-iter8-401`
- Stack: FastAPI + pydantic-ai + Redis sessions
- Config: pydantic-settings + `.env`
- Deployment: Fly.io
- Mode: lightweight
- Session semantics: app owns `session_id` (server-generated UUID in Redis, returned as `X-Session-ID`) -> `agentic_session(session_id=...)` REQUIRED around pydantic-ai calls; framework auto-instrumentation alone cannot link the app-owned ID.

Simulated answer: confirmed.

## Checkpoint 2 — PLAN (AskUserQuestion #2, multiSelect)

Proposed evaluators (one per failure category, no overlap):
- Task Completion (usefulness)
- RAG Faithfulness (correctness over retrieved docs)
- Answer Relevancy (comprehension)

Plan:
- Install `kelet` via uv
- `kelet.configure(api_key=..., project=...)` inside FastAPI `lifespan` at startup (explicit kwargs because `pydantic-settings` doesn't populate `os.environ`)
- `kelet.shutdown()` inside lifespan `finally:` block so BatchSpanProcessor flushes before Fly.io rotates the VM
- Wrap both `chat_agent.iter(...)` sites in `async with kelet.agentic_session(session_id=...)` — SSE route uses the persisted Redis `session_id`; stateless GET mints a one-shot UUID
- No VoteFeedback (no React)
- Keys written to `.env` + `.env.example`; `.env` already gitignored; production set via `fly secrets set`

Simulated answers:
- Evaluators: Task Completion + RAG Faithfulness + Answer Relevancy (all three picked)
- Plan: approved
- Project name: `docs-ai-iter8-401`
- API key mode: Paste secret key -> `sk-typo-wrong`

## Creating the evaluators — attempt 1 (typo'd key)

Banner shown before the curl:

> ⏳ Creating your evaluators. This takes 1–3 minutes (sometimes up to 5) — Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

### Curl (verbatim)

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-iter8-401/synthetics" \
  -H "Authorization: Bearer sk-typo-wrong" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Docs Q&A agent answering questions from a documentation corpus using BM25 retrieval + pydantic-ai","ideas":[{"id":"task-completion","name":"Task Completion","description":"Did the agent accomplish the user goal of getting a useful answer from the docs?","evaluator_type":"llm"},{"id":"rag-faithfulness","name":"RAG Faithfulness","description":"Does the answer stay faithful to the retrieved docs pages, without contradiction or fabrication?","evaluator_type":"llm"},{"id":"answer-relevancy","name":"Answer Relevancy","description":"Is the response on-topic and directly addressing the user question, without padding or drift?","evaluator_type":"llm"}]}'
```

### Response (verbatim)

```
{"detail":"Not authenticated"}
401
```

## 401 diagnosis + re-prompt (AskUserQuestion #3)

Parsed last line as HTTP status -> 401. Body: `{"detail":"Not authenticated"}`.

Surfaced to developer:

> The Kelet API returned **401 Not authenticated** for that key. It looks invalid — most likely a typo or wrong key type. Secret keys start with `sk-kelet-...` (no trailing whitespace, no quotes). Paste a corrected `KELET_API_KEY` to retry. I am NOT falling back to the deeplink — you clearly want to paste a key, so let's retry properly.

Decision: re-prompt for the key (do NOT fall back to deeplink; per skill + eval note, developer clearly intends to paste a key).

Simulated answer: `sk-kelet-eval-test`.

## Creating the evaluators — attempt 2 (corrected key)

### Curl (verbatim)

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-iter8-401/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Docs Q&A agent answering questions from a documentation corpus using BM25 retrieval + pydantic-ai","ideas":[{"id":"task-completion","name":"Task Completion","description":"Did the agent accomplish the user goal of getting a useful answer from the docs?","evaluator_type":"llm"},{"id":"rag-faithfulness","name":"RAG Faithfulness","description":"Does the answer stay faithful to the retrieved docs pages, without contradiction or fabrication?","evaluator_type":"llm"},{"id":"answer-relevancy","name":"Answer Relevancy","description":"Is the response on-topic and directly addressing the user question, without padding or drift?","evaluator_type":"llm"}]}'
```

### Response (verbatim)

```
created=3 updated=0 failed=0 deduped=false
200
```

### Success banner

> ✅ Created 3 evaluators in docs-ai-iter8-401: Task Completion, RAG Faithfulness, Answer Relevancy. First results in ~3min at https://console.kelet.ai/docs-ai-iter8-401/signals

## Implementation (after ExitPlanMode)

Files changed:
- `pyproject.toml` — add `kelet>=0.1`
- `src/settings/__init__.py` — add `kelet_api_key`, `kelet_project` fields
- `app/main.py` — import `kelet`; `kelet.configure(api_key=..., project=...)` on startup (gated on api_key only); `kelet.shutdown()` in lifespan `finally:`
- `src/routers/chat.py` — wrap SSE `_run_agent_stream` body in `async with kelet.agentic_session(session_id=session.session_id)` (wraps the ENTIRE generator including the `[DONE]` sentinel); wrap stateless GET with a one-shot UUID
- `.env` — `KELET_API_KEY=sk-kelet-eval-test`, `KELET_PROJECT=docs-ai-iter8-401`
- `.env.example` — documented both vars + `fly secrets set` note for production

`.env` was already in `.gitignore`.

## Verify

- pydantic-ai auto-instruments LLM spans — `configure()` alone captures model calls; `agentic_session()` links them to the app-owned Redis session_id
- `kelet.shutdown()` wired inside lifespan `finally:` — spans flush before Fly.io VM rotation
- Secret key server-only (no React/frontend in this repo)
- Session ID consistent: client -> server -> `agentic_session(session_id=session.session_id)` -> `X-Session-ID` response header (already exposed by CORS middleware)
- No hardcoded project name — read from `KELET_PROJECT` env var via Pydantic Settings

## Question budget

Total `AskUserQuestion` calls: 3 (Checkpoint 1 + Checkpoint 2 + recovery re-prompt). At the cap — justified because the 401 recovery requires a fresh input from the developer.
