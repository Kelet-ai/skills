# Kelet Integration Transcript — docs-ai (FastAPI + pydantic-ai + React)

> Developer said: **"integrate kelet into my app"**

---

## Welcome

**Kelet** is an AI agent that performs Root Cause Analysis on AI app failures. It ingests traces and signals, clusters failure patterns, and suggests fixes.

Core concepts, briefly:

- **Trace** — one LLM call recorded automatically: model, inputs/outputs, latency, tokens, errors.
- **Session** — all the traces that belong to one unit of work (one conversation).
- **Signal** — a pointer you drop at a meaningful moment: thumbs-down, edit, abandon, retry.
- **Synthetic** — a platform-managed signal that Kelet computes from the trace — no code from you.
- **Project** — a boundary for one agentic use case.

What's ahead: silent analysis, then at most 2–3 questions.

---

## Silent Analysis Pass

Read `pyproject.toml`, `app/main.py`, `src/routers/chat.py`, `src/agent/__init__.py`, `src/cache/__init__.py`, `src/settings/__init__.py`, `.env`, `frontend/`, `k8s/`, `docker-compose.yml`, `Dockerfile`.

Findings:

- **Deps** — FastAPI, pydantic-ai ≥1.0.15, redis-asyncio, jinja2, `kelet>=1.3.0` already present.
- **Entrypoint** — `app/main.py` (uvicorn `main:app`).
- **LLM call sites** — two flows, both call `chat_agent.iter()`:
  - `POST /chat` — stateful, SSE streaming, multi-turn.
  - `GET /chat` — stateless one-shot.
- **Session tracking** — **Redis-owned UUID**. `src/cache/__init__.py::create_session` calls `uuid.uuid4()` and stores under `docs-ai:session:<uuid>`. Session is returned to the browser via the `X-Session-ID` response header. pydantic-ai has no idea about this ID — Kelet's framework-level auto-instrumentation can't link traces to it. **`agentic_session(session_id=...)` is REQUIRED.**
- **Existing feedback UI** — none. Frontend directory is empty — need to scaffold.
- **Identity** — no stable user identity in the app, no `user_id` concept. (No PII concern; `user_id=` omitted correctly.)
- **Deployment** — Fly.io for backend (`fly.toml` not present but referenced in README / .env comments), Vercel for frontend. Helm chart for K8s also present.

---

## Checkpoint 1 — Mapping

```
                  Browser (React Vite UI, to scaffold)
                   │  POST /chat  { message, session_id? }
                   ▼
         ┌─────────────────────────┐
         │ FastAPI (app/main.py)   │
         │ └─ routers/chat.py      │
         │      └─ chat_agent.iter │──► pydantic-ai → LLM (Bedrock/OpenAI)
         │           └─ tools: search_docs, get_page (BM25)
         │ ⎯ session_id: Redis-owned UUID ⎯
         │   returned in X-Session-ID header
         └─────────────────────────┘
                   ▲
                   │ X-Session-ID  ◀──  React state (sessionIdRef)
                   │                    VoteFeedback uses same id
                   ▼
        React UI ──► 👍 / 👎 via VoteFeedback (@kelet-ai/feedback-ui)
```

Project map:

```
Use case: docs Q&A assistant over llms.txt
Flows → Kelet projects:
  - docs Q&A (single flow) → project "docs-ai-react-eval"
User-facing: yes (browser chat UI)
Stack: FastAPI + pydantic-ai; React 18 + Vite (scaffolded)
Config: .env (server) + frontend/.env (Vite)
Deployment: Fly.io (backend) + Vercel (frontend)
Mode: lightweight (kelet.configure + agentic_session + VoteFeedback + managed synthetics)
```

Workflow summary: user asks a question → agent uses BM25 to search indexed docs → retrieves full page content via `get_page` → drafts an answer grounded in the docs. Success: answer is faithful to the retrieved content and on-topic. Failure: hallucinated facts, off-topic padding, or an empty refusal.

> **AskUserQuestion #1:** _Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?_
> **Developer:** confirmed.

---

## Signal Analysis (internal — not shown to user)

- RAG agent (BM25 + `get_page`) → faithfulness is the core failure mode → `RAG Faithfulness` preset.
- Task Completion is the universal anchor.
- Off-topic/padding/refusal is a realistic failure on docs bots → `Answer Relevancy`.
- All three are captured by the trace alone → **managed synthetics**, zero customer code.
- Frontend has no feedback UI today. Low-cost, highest-diagnostic-value signal to add: `VoteFeedback` on each AI reply (wired to the server-owned session ID). One coded signal only — stay lightweight.

---

## Checkpoint 2 — Plan + Inputs

**Plan (lightweight):**

1. Backend: `kelet.configure()` at startup in `app/main.py`. Wrap both `chat_agent.iter` call-sites in `kelet.agentic_session(session_id=...)` using the Redis-owned `session.session_id` — required because the app owns the session ID, not pydantic-ai.
2. Frontend: scaffold Vite + TS + React 18. `KeletProvider` at root. `VoteFeedback` under each assistant bubble, `session_id` = the value returned by the server in `X-Session-ID`.
3. Env: `KELET_API_KEY` + `KELET_PROJECT` in server `.env`; `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT` in `frontend/.env`.
4. Platform synthetics via API.

**What you'll see:**

| After implementing                | Visible in Kelet console                             |
| --------------------------------- | ---------------------------------------------------- |
| `kelet.configure()`               | LLM spans in Traces: model, tokens, latency, errors  |
| `agentic_session()`               | Sessions view: full conversation grouped for RCA     |
| VoteFeedback                      | Signals: 👍/👎 correlated to exact trace             |
| Platform synthetics               | Signals: automated quality scores                    |

> **AskUserQuestion #2:** _Pick evaluators + confirm plan + keys/project + key mode._
> **Developer:** selected all three evaluators (Task Completion, RAG Faithfulness, Answer Relevancy); plan approved; scaffold React yes; `KELET_API_KEY=sk-kelet-eval-test`; `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test`; project `docs-ai-react-eval`; key mode: **paste secret key**.

---

## Creating synthetic evaluators

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) — Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-react-eval/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Documentation Q&A agent (docs-ai). pydantic-ai agent answers user questions strictly from indexed llms.txt documentation using BM25 search. Two tools: search_docs and get_page. Multi-turn sessions via Redis-backed session_id. FastAPI backend + React chat UI.","ideas":[{"id":"task-completion","name":"Task Completion","description":"Did the agent actually answer the user question using the docs, or leave them hanging?","evaluator_type":"llm"},{"id":"rag-faithfulness","name":"RAG Faithfulness","description":"Do the agent claims match the retrieved doc content, or does it invent facts outside the indexed docs?","evaluator_type":"llm"},{"id":"answer-relevancy","name":"Answer Relevancy","description":"Is the answer on-topic to the question, or padded / deflecting?","evaluator_type":"llm"}]}'
```

Response:

```
created=3 updated=0 failed=0 deduped=false
200
```

✅ Kelet is now watching `docs-ai-react-eval`. First evaluator results in ~3min at https://console.kelet.ai/docs-ai-react-eval/signals

---

## Implementation (applied)

**Server**

- `app/main.py`: `import kelet` + `kelet.configure()` at module level. Reads `KELET_API_KEY` + `KELET_PROJECT` eagerly from env.
- `src/routers/chat.py`:
  - `POST /chat` SSE path: `async with kelet.agentic_session(session_id=session.session_id):` wraps `chat_agent.iter(...)`. The `session.session_id` is the **same** UUID returned to the browser in `X-Session-ID`.
  - `GET /chat` stateless path: one-shot UUID so the trace still groups under a session.
- `src/settings/__init__.py`: `kelet_project` default updated to `docs-ai-react-eval`.
- `.env`: `KELET_API_KEY=sk-kelet-eval-test`, `KELET_PROJECT=docs-ai-react-eval`.

**Frontend (new, `frontend/`)**

- Vite + TS + React 18 minimal chat UI.
- `main.tsx`: `<KeletProvider apiKey={VITE_KELET_PUBLISHABLE_KEY} project={VITE_KELET_PROJECT}>` at root.
- `App.tsx`: streams SSE from `POST /chat`, captures `X-Session-ID` header into a sticky `sessionIdRef`, attaches it to each assistant message as `sessionId`, and renders `<VoteFeedback.Root session_id={msg.sessionId}>` under each assistant bubble — so the signal and the server's `agentic_session` share the exact same ID.
- `VoteFeedback.UpvoteButton` / `DownvoteButton` use `asChild` + styled `<button>` children per the API reference (no nested `<button><button>` bug).
- `frontend/.env`: `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test`, `VITE_KELET_PROJECT=docs-ai-react-eval`.

---

## Phase V — Verification checklist

- Every agentic entry point (POST /chat, GET /chat) covered by `agentic_session()` ✅
- Session ID consistent end-to-end: Redis → `session.session_id` → `agentic_session(session_id=...)` → `X-Session-ID` header → React `sessionIdRef` → `VoteFeedback.Root session_id={...}` ✅
- `kelet.configure()` called once at module import (not per-request) ✅
- Secret key server-only (`KELET_API_KEY` in backend `.env`); publishable key (`VITE_...`) in frontend only ✅
- Mode: lightweight — `configure()` + `agentic_session()` + 1 coded signal (VoteFeedback) + 3 managed synthetics. No coded `source=SYNTHETIC`. No edit/retry/copy signals added (out of scope for plain chat).
- `document.querySelectorAll('button button').length === 0` — guaranteed by `asChild` usage; `VoteFeedback.*Button` does NOT render its own `<button>` when `asChild` is set.
