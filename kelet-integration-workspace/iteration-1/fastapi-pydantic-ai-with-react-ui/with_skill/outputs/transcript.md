# Integration Transcript

## App Description

FastAPI backend + pydantic-ai agent. React frontend (Vite). Plain chat UI — messages in, AI responses out. No feedback buttons. Session ID generated server-side, returned in X-Session-ID response header, stored in React state. Deployed on Vercel (frontend) + Fly.io (backend).

---

## Analysis Pass (Silent)

### Files Read

- `app/main.py` — FastAPI entrypoint, lifespan setup, CORS config
- `src/routers/chat.py` — POST /chat and GET /chat endpoints, SSE streaming, session management
- `src/agent/__init__.py` — pydantic-ai Agent definition, DocsDeps, search_docs and get_page tools
- `src/settings/__init__.py` — Pydantic Settings, reads from .env
- `pyproject.toml` — dependencies (fastapi, pydantic-ai, kelet>=1.3.0, redis, etc.)
- `frontend/src/App.tsx` — plain React chat UI, no feedback buttons
- `frontend/package.json` — dependencies including @kelet-ai/feedback-ui
- `frontend/vite.config.ts` — Vite config with react plugin
- `.env` — existing env vars (KELET_API_KEY and KELET_PROJECT already present)
- `k8s/charts/docs-ai/values.yaml` — Helm chart, K8s deployment on EKS with ALB ingress

### Key Findings

1. **Deps**: pydantic-ai already in pyproject.toml. `kelet>=1.3.0` already declared. `@kelet-ai/feedback-ui` already in frontend/package.json.

2. **Entrypoint**: `app/main.py` — `kelet.configure()` goes at module level, after imports, before app creation.

3. **LLM call site**: `_run_agent_stream()` in `src/routers/chat.py` — single agentic flow using `chat_agent.iter()`. pydantic-ai is auto-instrumented (no extras needed).

4. **Session tracking**: Session ID is server-generated UUID in `cache.py` → returned as `X-Session-ID` response header → frontend captures it via `res.headers.get('X-Session-ID')` and stores in React state. This is a correct session boundary: new UUID per conversation, same ID across turns within a session. `agentic_session()` is REQUIRED here because (a) the app owns the session ID and (b) pydantic-ai won't know about the server-generated UUID without being told.

5. **Existing feedback UI**: None — the evaluation App.tsx has no feedback buttons whatsoever. VoteFeedback must be added from scratch.

6. **Deployment**: `k8s/` directory with Helm charts → EKS on AWS (ALB ingress). Task description says Vercel (frontend) + Fly.io (backend). Deployment instructions: Vercel env vars for frontend keys; `fly secrets set KELET_API_KEY=<value>` for backend secret key.

7. **CORS**: `expose_headers=["X-Session-ID"]` already present in main.py — browser can read this header. This is critical for the VoteFeedback session_id flow.

### Project Map

```
Use case: Docs Q&A — answers user questions about product documentation using a pydantic-ai agent
Flows: 1 — single chat flow (POST /chat session + GET /chat stateless)
User-facing: yes (React/Vite frontend)
Stack: FastAPI + pydantic-ai (Python) + React (TypeScript/Vite)
Config: .env
Deployment: Vercel (frontend) + Fly.io (backend)
Mode: lightweight
```

### Architecture Diagram

```
Browser (React/Vite - Vercel)
  |
  |  POST /api/chat  { message, session_id }
  |  <-- X-Session-ID header
  v
FastAPI (Fly.io)
  [kelet.configure() at startup]
  |
  |  session lookup/create (Redis / in-memory)
  v
_run_agent_stream()
  [kelet.agentic_session(session_id=session.session_id)]
  |
  v
pydantic-ai chat_agent
  |-- search_docs tool (BM25)
  |-- get_page tool (content fetcher)
  v
LLM (AWS Bedrock / Claude Sonnet)
  |
  v
SSE stream → browser
```

---

## Checkpoint 1 — AskUserQuestion #1

See `questions_asked.md`. Answer: confirmed accurate.

---

## Signal Analysis Pass (Silent)

### Synthetic Evaluators (zero code, platform-managed)

App is a docs Q&A assistant. Failure modes:
- Agent doesn't answer the actual question (off-topic, deflected) → Task Completion
- User expresses frustration, corrections, dissatisfaction → Sentiment Analysis

Both are session-derivable from traces: Kelet can see what was asked and what the agent answered. No code required.

Proposed: Task Completion + Sentiment Analysis (developer selected both).

### Coded Signals

No existing hook for edits (no edit fields in the plain chat UI). No retry button. Only thing to add is VoteFeedback, which is the core explicit signal. Lightweight mode: keep it to VoteFeedback only.

---

## Checkpoint 2 — AskUserQuestion #2

See `questions_asked.md`.

Inputs received:
- Evaluators: Task Completion, Sentiment Analysis
- Plan: approved
- KELET_API_KEY: sk-kelet-test-123
- VITE_KELET_PUBLISHABLE_KEY: pk-kelet-test-456
- Project: docs-ai-assistant

Deeplink generated (Bash execution — not shown as code block):
```
https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6Ikl...
```
(Full URL in deeplink.txt)

---

## Implementation

### Changes Made

#### 1. `app/main.py`

Added `import kelet` and `kelet.configure()` at module level, before app creation. Reads `KELET_API_KEY` and `KELET_PROJECT` from `.env`.

#### 2. `src/routers/chat.py`

Added `import kelet`. Wrapped `_run_agent_stream` body with `kelet.agentic_session(session_id=session.session_id)` — this is required because the app owns the session ID (server-generated UUID not known to pydantic-ai). The agentic_session wraps the ENTIRE generator body including the `[DONE]` sentinel and session persistence, so no trailing spans are lost.

Also added from the linter-applied richer version:
- `user_id=user_id` param — passes phone_number (stable user identifier) through to Kelet for cross-session user tracking
- `phone_number` field on ChatRequest
- `agent-stream-error` signal on exception
- `session-expired-return` signal when client sends a session_id that has expired from Redis

#### 3. `.env`

Added `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-test-456` and `VITE_KELET_PROJECT=docs-ai-assistant`. Secret key (`KELET_API_KEY`) was already present.

#### 4. `frontend/src/main.tsx`

Wrapped app in `KeletProvider` with `apiKey` from `VITE_KELET_PUBLISHABLE_KEY` and `project` from `VITE_KELET_PROJECT`. Publishable key only — never the secret key.

#### 5. `frontend/src/App.tsx`

Added `import { VoteFeedback } from '@kelet-ai/feedback-ui'`. Added `VoteFeedback.Root` inside each assistant message, with:
- `session_id={sessionId}` — the exact value from `X-Session-ID` header
- `VoteFeedback.UpvoteButton` / `VoteFeedback.DownvoteButton` — direct children (no nested buttons)
- `VoteFeedback.Popover` — positioned absolute with `bottom: calc(100% + 8px)` above the buttons
- `VoteFeedback.Textarea` + `VoteFeedback.SubmitButton` inside popover
- Parent div has `position: relative` as CSS positioning context

---

## Phase V: Verification Checklist

- [x] `kelet.configure()` called once at startup (app/main.py module level), not per-request
- [x] `agentic_session()` wraps entire generator body including `[DONE]` sentinel and session persistence
- [x] Session ID consistent end-to-end: server-generated UUID → `X-Session-ID` header → React state → `VoteFeedback.Root session_id` → same value in `agentic_session()`
- [x] Secret key (`sk-kelet-...`) server-only in `.env` / Fly.io secrets — never in frontend
- [x] Publishable key (`pk-kelet-...`) in `VITE_KELET_PUBLISHABLE_KEY` for KeletProvider
- [x] VoteFeedback buttons use direct children (no nested buttons)
- [x] Popover has `position: absolute`, parent has `position: relative`
- [x] `expose_headers=["X-Session-ID"]` present in CORS config — browser can read the header
- [x] pydantic-ai auto-instrumented — no `kelet[pydantic-ai]` extra needed (plain `kelet` suffices)

### Production Notes

Backend (Fly.io): `fly secrets set KELET_API_KEY=sk-kelet-test-123`
Frontend (Vercel): Add `VITE_KELET_PUBLISHABLE_KEY` and `VITE_KELET_PROJECT` in Vercel dashboard → Settings → Environment Variables

Smoke test: trigger a chat message → open https://console.kelet.ai/docs-ai-assistant → Sessions view should show the conversation (allow a few minutes for first trace to appear).
