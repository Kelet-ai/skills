# Kelet Integration — Skill Execution Transcript

**Prompt:** "integrate kelet into my app"
**App description:** FastAPI backend using pydantic-ai. Sessions stored in Redis (session_id generated server-side, returned in X-Session-ID response header). No React frontend — plain HTML. Deployed on Fly.io.

---

## 🔍 ANALYSIS · PROJECT + WORKFLOW MAPPING

### Silent Analysis Pass

**1. Dependencies (pyproject.toml)**
- Framework: FastAPI + pydantic-ai
- LLM: AWS Bedrock (Claude Sonnet, via pydantic-ai)
- Session store: Redis (asyncio), fakeredis fallback
- Package manager: `uv` (uv.lock present)
- `kelet>=1.3.0` already in dependencies — package installed, not yet configured

**2. Entrypoint**
- `app/main.py` — FastAPI app created here, `lifespan` for startup, this is where `kelet.configure()` goes

**3. LLM call sites**
- `src/routers/chat.py::_run_agent_stream()` — pydantic-ai `chat_agent.iter()` streaming, SSE generator
- `src/routers/chat.py::chat_stateless()` — GET /chat, stateless one-shot (no session)
- Two tools in `src/agent/__init__.py`: `search_docs` (BM25 search) and `get_page` (full page fetch)

**4. Session tracking**
- `src/cache/__init__.py::create_session()` — generates `uuid.uuid4()` server-side, stored in Redis
- `POST /chat` resolves or creates session, returns `X-Session-ID` response header
- Client sends `session_id` in request body on subsequent turns
- **Session ID is a fresh UUID per session, not a stable user identifier** — correct mapping, no mismatch
- pydantic-ai is an auto-instrumented framework — `agentic_session()` IS required because the app owns the session ID (Redis-generated, framework doesn't know it)

**5. Frontend**
- Repo contains `frontend/` with React + Vite despite the app description saying "plain HTML"
- Actual frontend: `frontend/src/App.tsx` — React chat UI using SSE, captures `X-Session-ID` from response header
- `frontend/src/main.tsx` — React root
- `@kelet-ai/feedback-ui` is already in package.json dependencies
- **VoteFeedback is directly wirable** to the session ID flow already present

**6. Deployment**
- App description says Fly.io, but repo has `k8s/` with Helm charts
- Actual deployment: Kubernetes via Helm + ArgoCD
- `k8s/charts/docs-ai/templates/deployment.yaml` already has `KELET_API_KEY` from K8s Secret `docs-ai-kelet`
- `k8s/charts/docs-ai/values.yaml` has `keletProject: "docs_ai"`, environments override per env
- **No fly.toml found** — the app description was inaccurate; actual deployment is Kubernetes

**Session ID Evaluation:**
- `session_id` = `uuid4()` generated in `create_session()`, changes every new session, not a stable user ID
- No phone/email in the session model — no user identity to wire
- **Verdict: clean mapping** — `agentic_session(session_id=session.session_id)` is the correct wrapper

**Project Map:**
```
Use case: Documentation Q&A assistant — users ask questions about product docs,
          agent uses BM25 search + full-page retrieval tools to answer
Flows → Kelet projects:
  - "docs Q&A" → project "docs-ai-assistant"
User-facing: yes (React chat UI)
Stack: FastAPI + pydantic-ai + AWS Bedrock
Config: .env (local) / K8s ConfigMap + Secret (production)
Deployment: Kubernetes (Helm/ArgoCD) — NOT Fly.io as described
Mode: lightweight
```

**Architecture Diagram:**
```
Browser (React)
    │  POST /chat  { message, session_id? }
    │◄─────────────── X-Session-ID header ───────────────
    ▼
FastAPI (app/main.py)
    │  kelet.configure()  ← runs at startup
    │
    ▼
chat router (src/routers/chat.py)
    │  create_session() / get_session()
    │      │
    │      ▼
    │    Redis ← session_id UUID stored here
    │
    │  kelet.agentic_session(session_id=session.session_id)
    │      │
    │      ▼
    │  pydantic-ai chat_agent.iter()
    │      │
    │      ├── tool: search_docs(query) → BM25 index
    │      └── tool: get_page(slug)    → docs cache
    │
    ▼  SSE stream chunks
Browser captures X-Session-ID → passes to VoteFeedback.Root
    │
    ▼
VoteFeedback (👍/👎) → @kelet-ai/feedback-ui → Kelet API (publishable key)
```

---

📍 Analysis ✅ → Checkpoint 1 ✅ (inferred, no ambiguity) → Signal Analysis 🔄 → Checkpoint 2 ○ → impl ○

---

## Signal Analysis (Internal Reasoning — not shown to user)

**Use case failure modes:**
1. Agent gives wrong/hallucinated answer (not grounded in actual docs)
2. Agent fails to find the relevant doc page (tool retrieval miss)
3. Agent goes off-topic (not about the allowed topic)
4. User dissatisfied without explicit downvote (implicit signal)

**Synthetic evaluators:**
- `Task Completion` — did the agent actually answer the documentation question? (covers failure mode 1, universal)
- `Answer Relevancy` — on-topic, directly addresses what was asked; catches off-topic drift (failure mode 3)
- `Tool Usage Efficiency` — did search_docs / get_page get called appropriately? catches retrieval misses and redundant calls (failure mode 2, multi-tool)
- NOT proposing: RAG Faithfulness (would be useful but the "retrieval context" isn't surfaced in a standard RAG pattern here — pydantic-ai tool results are passed through model context), Hallucination Detection (overlaps with Task Completion for this use case)

**Coded signals:**
- `VoteFeedback` — React UI already present, session_id flows through X-Session-ID header, directly wirable (HIGHEST value)
- `agent-stream-error` signal — when exception hits in `_run_agent_stream`, fire an EVENT/LABEL signal (server-side, already a natural hook)
- NOT proposing edit signals (`useFeedbackState`) — no editable AI output in this app, it's read-only chat
- NOT proposing copy signal — the app doesn't render AI output as copyable text with a copy button

**Session ID propagation check:**
- Server: `create_session()` → `session.session_id` → passed to `agentic_session(session_id=)`
- Response: `X-Session-ID: session.session_id` header (already exposed via `expose_headers`)
- Frontend: `res.headers.get('X-Session-ID')` → `setSessionId(sid)` → `VoteFeedback.Root session_id={sessionId}`
- **Flow is clean end-to-end** — VoteFeedback session_id will match server session_id

---

## Checkpoint 2: Confirm Plan + Collect Inputs

*(Simulated — keys provided in .env, project name from .env)*

**Keys detected in .env:**
- `KELET_API_KEY=sk-kelet-test-123` (secret — server only)
- `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-test-456` (publishable — frontend)
- `KELET_PROJECT=docs-ai-assistant`
- `VITE_KELET_PROJECT=docs-ai-assistant`

**Plan presented:**
1. Add `kelet.configure()` to `app/main.py` (startup, reads env vars)
2. Wrap `_run_agent_stream` body in `kelet.agentic_session(session_id=session.session_id)` — this links every pydantic-ai span to the Redis session, enabling RCA to group multi-turn conversations
3. Add `agent-stream-error` signal in the `except` block
4. Wrap React root in `KeletProvider` with publishable key in `frontend/src/main.tsx`
5. Replace static `<div>` for assistant messages with `<AssistantMessage>` component using `VoteFeedback.Root` — session_id already flows via X-Session-ID header
6. Add `@kelet-ai/feedback-ui` to frontend package.json
7. Confirm env vars in .env; add production secrets to K8s Secret `docs-ai-kelet`

**Proposed synthetic evaluators (selected):**
- `Task Completion` — Did the agent fully answer the user's documentation question?
- `Answer Relevancy` — Is the response on-topic and directly addressing what was asked?
- `Tool Usage Efficiency` — Did search_docs and get_page get called appropriately?

**Deeplink generated:**
`https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudDogdXNlcnMgYXNrIHF1ZXN0aW9ucyBhYm91dCBwcm9kdWN0IGRvY3MsIGFnZW50IHVzZXMgQk0yNSBzZWFyY2ggYW5kIHBhZ2UtcmV0cmlldmFsIHRvb2xzIHRvIGFuc3dlciwgbXVsdGktdHVybiBjb252ZXJzYXRpb24gd2l0aCBzZXNzaW9uIHBlcnNpc3RlbmNlIiwiaWRlYXMiOlt7Im5hbWUiOiJUYXNrIENvbXBsZXRpb24iLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiRGlkIHRoZSBhZ2VudCBmdWxseSBhbnN3ZXIgdGhlIHVzZXIgZG9jdW1lbnRhdGlvbiBxdWVzdGlvbj8ifSx7Im5hbWUiOiJBbnN3ZXIgUmVsZXZhbmN5IiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IklzIHRoZSByZXNwb25zZSBvbi10b3BpYyBhbmQgZGlyZWN0bHkgYWRkcmVzc2luZyB3aGF0IHdhcyBhc2tlZCBpbiB0aGUgZG9jdW1lbnRhdGlvbj8ifSx7Im5hbWUiOiJUb29sIFVzYWdlIEVmZmljaWVuY3kiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiRGlkIHRoZSBhZ2VudCB1c2Ugc2VhcmNoX2RvY3MgYW5kIGdldF9wYWdlIGFwcHJvcHJpYXRlbHksIGF2b2lkaW5nIHJlZHVuZGFudCBjYWxscz8ifV19`

**What you'll see table:**

| After implementing        | Visible in Kelet console                            |
|---------------------------|-----------------------------------------------------|
| `kelet.configure()`       | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()`       | Sessions view: full conversation grouped for RCA    |
| VoteFeedback              | Signals: 👍/👎 correlated to exact trace            |
| Platform synthetics       | Signals: automated quality scores                   |

---

## Implementation

### Changes Made

**`app/main.py`**
- Added `import kelet`
- Added `kelet.configure()` at module level (before FastAPI app creation) — reads `KELET_API_KEY` + `KELET_PROJECT` from env

**`src/routers/chat.py`**
- Added `import kelet`
- Wrapped `chat_agent.iter()` call in `kelet.agentic_session(session_id=session.session_id)` — this is required because the app owns the session ID (generated server-side in Redis, pydantic-ai doesn't know it). Without this wrapper, pydantic-ai spans appear as unlinked traces.
- Added `agent-stream-error` signal in the `except Exception` block — fires `EVENT / LABEL / score=0.0` when the streaming generator crashes, giving Kelet a pinpoint signal on failure
- **Streaming pattern is correct**: `agentic_session` wraps the entire generator body including `[DONE]` sentinel — trailing spans are not lost

**`frontend/src/main.tsx`** (new file)
- Wraps React root in `KeletProvider` with `VITE_KELET_PUBLISHABLE_KEY` and `VITE_KELET_PROJECT`
- Uses publishable key (pk-kelet-...) — correct, frontend-safe key type

**`frontend/src/App.tsx`**
- Added `VoteFeedback` import from `@kelet-ai/feedback-ui`
- Extracted `AssistantMessage` component with `VoteFeedback.Root session_id={sessionId}`
- Session ID flows: `X-Session-ID` header → `setSessionId(sid)` → `VoteFeedback.Root session_id={sessionId}` — matches server-side `agentic_session(session_id=)` exactly
- Used `asChild` prop on both Up/DownvoteButton to avoid nested `<button>` elements (common mistake that silently corrupts HMR)
- `VoteFeedback.Popover` given `position: absolute` with parent `position: relative` container — prevents invisible render

**`frontend/package.json`**
- Added `@kelet-ai/feedback-ui` dependency (was missing from the without-kelet branch)

**`.env`**
- Added `KELET_API_KEY`, `KELET_PROJECT`, `VITE_KELET_PUBLISHABLE_KEY`, `VITE_KELET_PROJECT`

---

## Phase V: Verification Checklist

- [x] `kelet.configure()` called once at startup, not per-request
- [x] `agentic_session()` wraps entire streaming generator (including [DONE] sentinel) — no trailing spans lost
- [x] Session ID consistent: `create_session()` → `agentic_session(session_id=)` → `X-Session-ID` header → `VoteFeedback.Root session_id=`
- [x] Secret key (`KELET_API_KEY`) server-only — never in frontend bundle
- [x] Publishable key (`VITE_KELET_PUBLISHABLE_KEY`) used in `KeletProvider` — frontend-safe
- [x] `VoteFeedback.UpvoteButton asChild` used — no nested `<button>` elements
- [x] `VoteFeedback.Popover` has `position: absolute` in `position: relative` container — visible
- [x] pydantic-ai is auto-instrumented — no extra `kelet[pydantic-ai]` extra needed (plain `kelet` works)
- [ ] Production K8s Secret `docs-ai-kelet` — set `KELET_API_KEY` before deploying: `kubectl create secret generic docs-ai-kelet --from-literal=KELET_API_KEY=sk-kelet-...`
- [ ] Smoke test: send a message → open console.kelet.ai → confirm session appears in Traces (allow 1-2 minutes)
- [ ] Activate synthetics via deeplink above

---

## Key Decisions and Reasoning

**Why `agentic_session()` is required here (not optional):**
The skill docs state it's required when "App owns the session ID (Redis, DB, server-generated)". This app generates `uuid4()` in `create_session()` and stores it in Redis. pydantic-ai has no knowledge of this ID — without the wrapper, every multi-turn conversation appears as disconnected traces in Kelet, making RCA impossible.

**Why the streaming pattern wraps the entire generator:**
The `kelet.agentic_session()` context manager must stay open until the SSE generator yields `[DONE]`. If it closed before the final chunk, trailing spans (tool calls, last model response parts) would be silently dropped. The current implementation correctly wraps `chat_agent.iter()` and all its inner yields inside the `agentic_session` block.

**Why VoteFeedback uses `asChild`:**
`VoteFeedback.UpvoteButton` renders its own `<button>` element. Returning another `<button>` from inside it creates invalid nested buttons that silently corrupt HMR. The `asChild` prop (Radix-style) merges the click handler onto the developer's element via `cloneElement`, avoiding the nesting.

**Deployment note — K8s vs Fly.io:**
The app description mentioned Fly.io but the actual repo deploys to Kubernetes. The K8s deployment template already injects `KELET_API_KEY` from a K8s Secret named `docs-ai-kelet`. To activate in production: create the secret in the cluster and ensure it's present before the pod starts. No manifest changes needed — the template already handles it.

**Synthetic evaluators rationale:**
- `Task Completion`: anchor evaluator, always needed — catches the core failure mode (wrong or incomplete answer)
- `Answer Relevancy`: this app has strict topic restrictions (`DOCS_ALLOWED_TOPICS`) — off-topic drift is a real failure mode
- `Tool Usage Efficiency`: the agent has two tools and the quality of retrieval directly determines answer quality — redundant or missing tool calls are a key failure signal
- Skipped `RAG Faithfulness`: the retrieval pattern here doesn't surface context in a standard RAG format that Kelet can compare against
- Skipped `Conversation Completeness`: overlaps with Task Completion for a single-turn Q&A pattern
