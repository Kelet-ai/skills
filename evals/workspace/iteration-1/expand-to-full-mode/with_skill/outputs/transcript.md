# Execution Transcript — Expand to Full Mode

**Skill version:** kelet-integration 1.4.0
**App:** docs-ai (FastAPI + pydantic-ai, plain HTML frontend)
**Branch:** without-kelet + simulated baseline (kelet.configure + agentic_session already wired)
**Mode:** Full (developer explicitly requested)

---

## Phase 1: Silent Analysis Pass

Read the following files:
- `app/main.py` — kelet.configure() present, module-level. Correct.
- `src/routers/chat.py` — kelet.agentic_session(session_id=..., user_id=phone_number) wrapping agent call. Correct.
- `src/agent/__init__.py` — pydantic-ai Agent with two tools: search_docs (BM25) and get_page (slug lookup). Neither wrapped in error handling. No kelet import.
- `src/cache/__init__.py` — Redis-backed ChatSession CRUD. session_id is UUID per conversation. user_id is phone_number (stable).
- `src/settings/__init__.py` — Pydantic Settings. KELET_API_KEY and KELET_PROJECT read from env.
- `.env` — KELET_API_KEY=sk-kelet-existing-123, KELET_PROJECT=docs-ai-assistant. Both present.
- `k8s/charts/docs-ai/values.yaml` + `k8s/environments/prod.yaml` — K8s Secret for KELET_API_KEY, keletProject in config. Confirmed prod deployment path.
- `.github/workflows/` — CI/CD pipeline. KELET_API_KEY not needed in CI (tests run with OTEL_SDK_DISABLED=true). No action needed.

**Project map:**
```
Use case: Documentation Q&A for Kelet platform
Flow: "docs chat" → project "docs-ai-assistant"
User-facing: yes (plain HTML, no React)
Stack: FastAPI + pydantic-ai (Bedrock Claude Sonnet)
Config: .env (local) + K8s Secret (prod)
Deployment: Kubernetes, ArgoCD, AWS ALB
Mode: full
```

**Session semantics:** UUID per conversation, Redis 30-min TTL. Phone number = stable user identity, correctly threaded as user_id=. No semantic issues detected.

---

## Phase 2: Signal Analysis Pass (Silent)

**Observed failure modes:**
1. Tool exceptions silently swallowed — `search_docs` and `get_page` have no error handling, no kelet instrumentation
2. Page not found — `get_page` returns a string when slug is missing; currently no signal
3. Agent stream error — `except Exception` in `_run_agent_stream` only logs and yields error SSE; Kelet has no visibility
4. Session abandonment — Redis TTL expiry is the only mechanism; no signal when user returns with expired session_id

**Synthetic evaluator candidates:**
- Task Completion — universal, high value for docs Q&A
- Sentiment Analysis — developers may express frustration with repeated corrections
- Conversation Completeness — multi-part questions are common in docs assistants
- Role Adherence — agent has a strict topic restriction (`docsAllowedTopics`); drift is a real failure mode

**Not selected:**
- RAG Faithfulness — not wired (would need retrieved context passed through)
- Hallucination Detection — overlaps with Role Adherence for this constrained use case
- Loop Detection — agent doesn't have iterative loops; BM25 + get_page are called once per request

**VoteFeedback decision:** Not applicable. Plain HTML frontend, no React. `@kelet-ai/feedback-ui` is React-only. No existing feedback hook in the HTML. Not added.

---

## Phase 3: Checkpoint 1 (Simulated)

AskUserQuestion: Architecture + workflow map confirmation.
**Developer response:** "Yes, looks accurate." → Proceeded.

---

## Phase 4: Checkpoint 2 (Simulated)

AskUserQuestion: Evaluator selection + plan confirmation + keys check.

**Simulated developer selections:**
- Evaluators: Task Completion, Sentiment Analysis, Conversation Completeness, Role Adherence
- Plan: approved
- Keys: already present in .env — no action needed
- Project name: docs-ai-assistant — confirmed

**Deeplink generated** (Bash execution):
`https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6...`

**"What you'll see" table (items in plan only):**

| After implementing | Visible in Kelet console |
|---|---|
| `kelet.configure()` | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()` | Sessions view: full conversation grouped for RCA |
| Tool error signals | Signals: tool-search-error, tool-page-error, tool-page-not-found correlated to session |
| Agent stream error signal | Signals: agent-stream-error with score=0.0 — marks hard failures |
| Session expiry signal | Signals: session-expired-return — implicit abandonment from user returning after TTL |
| Platform synthetics | Signals: Task Completion, Sentiment, Completeness, Role Adherence on every session |

---

## Phase 5: Implementation

### Skipped (already present in baseline)
- `kelet.configure()` in `app/main.py`
- `kelet.agentic_session(session_id=..., user_id=...)` in `src/routers/chat.py`
- `KELET_API_KEY` and `KELET_PROJECT` in `.env`
- `phone_number` field in `ChatRequest` and `user_id=body.phone_number` in stream call

### Added

**`src/agent/__init__.py`:**
- Added `import kelet` and `import logging` + `logger`
- Converted `search_docs` and `get_page` tools from sync to async (required for await kelet.signal())
- Added try/except to `search_docs`: catches exceptions, fires `tool-search-error` signal
- Added try/except to `get_page`: fires `tool-page-not-found` when slug returns None, fires `tool-page-error` on exception

**`src/routers/chat.py`:**
- Added `await kelet.signal("EVENT", "LABEL", ..., trigger_name="agent-stream-error", score=0.0)` in the except block of `_run_agent_stream`
- Added session expiry detection in `chat()` POST handler: if `body.session_id` provided but `get_session` returns None, fires `session-expired-return` signal with the expired session_id in metadata

### Not added
- VoteFeedback — no React frontend
- source=SYNTHETIC code — platform handles all evaluators
- Rate limit signals — not requested, adds noise (rate limiting is a platform/infra concern, not an agent quality signal)
- Feedback endpoint — developer did not request it; no existing frontend hook to wire it to

---

## Phase 6: Verification Checklist

- [x] kelet.configure() called once at startup (app/main.py module level)
- [x] agentic_session() wraps every agent call in the session endpoint
- [x] KELET_API_KEY is sk-kelet-... (secret) — server-only, not in frontend bundle
- [x] KELET_PROJECT set via env var, not hardcoded
- [x] session_id is UUID per conversation, not stable user identity
- [x] phone_number correctly passed as user_id= (stable) not session_id
- [x] Tool functions converted to async — required for await kelet.signal() inside @chat_agent.tool
- [x] Signal kind/source/trigger_name follow naming convention (source-action, lowercase, hyphenated)
- [ ] Smoke test pending: trigger LLM call → verify session in Kelet console (allow a few minutes)
- [ ] Activate synthetics deeplink at console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=...

**Key silent failure mode to watch:** pydantic-ai is auto-instrumented (on supported framework list) — `agentic_session()` is still required here because the app owns the session ID (Redis-generated UUID). Without it, VoteFeedback linkage would break and spans would appear unlinked. This is correctly wired.
