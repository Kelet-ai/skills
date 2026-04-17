# Kelet Integration Skill Transcript

**App:** docs-ai (FastAPI + pydantic-ai documentation Q&A assistant)
**Developer context:** FastAPI + pydantic-ai. User identity = phone number stored in DB. No per-conversation UUID — phone number is the only identifier. Multi-turn chat, users can start fresh conversations.
**Skill version:** 1.4.0
**Mode:** Lightweight

---

## Welcome + Concept Teaching

Presented Kelet concepts before any code:
- **Trace** — automatic recording of one LLM call or tool invocation
- **Session** — group of traces for one conversation; how Kelet correlates multi-turn behavior
- **Signal** — a tip at a meaningful moment (thumbs-down = start looking here)
- **Synthetic** — automated signal Kelet runs on every session from trace data (no code)
- **Project** — logical boundary for one use case; wrong project = silent routing failure

---

## Analysis Pass (Silent)

**Step 1: Dependencies**
- `pyproject.toml`: `kelet>=1.3.0` already in dependencies — skip install step
- Framework: `pydantic-ai>=1.0.15` — auto-instrumented by Kelet
- No frontend dependencies — server-side only (no React, no publishable key needed)
- Package manager: `uv.lock` present → uv

**Step 2: Entrypoint**
- `app/main.py` — FastAPI lifespan startup; `kelet.configure()` goes here at module level (once at startup, not per-request)

**Step 3: LLM Call Sites**
- `src/routers/chat.py` — `_run_agent_stream()`: main agent execution via `chat_agent.iter()`
- `src/routers/chat.py` — `chat_stateless()`: GET /chat for one-shot queries (no session)
- `src/agent/__init__.py` — `chat_agent` defined with pydantic-ai, two tools: `search_docs`, `get_page`
- Failure modes: doc retrieval miss (wrong BM25 results), hallucination, off-topic responses, rate limiting

**Step 4: Session Tracking (CRITICAL)**
- `src/cache/__init__.py`: `create_session()` generates `str(uuid.uuid4())` — fresh UUID per conversation
- Sessions stored in Redis: key `docs-ai:session:<uuid>`, TTL 1800s (30 min)
- `ChatRequest.session_id: str | None = None` — client sends back UUID on subsequent turns
- Session auto-created when `session_id` not provided or expired
- UUID returned to client via `X-Session-ID` response header
- **Developer said "phone is the only identifier"** — but code already generates UUIDs ✓
- **Mismatch flagged:** phone outlives sessions; should be `user_id=` not `session_id`
- **Fix:** add `phone_number: str | None` to `ChatRequest`; pass as `user_id` to `kelet.agentic_session()`
- `agentic_session()` REQUIRED: app owns the session ID (Redis-generated UUID); framework doesn't know it

**Step 5: Existing Feedback UI**
- None — no frontend in this repo (pure API service)
- VoteFeedback not applicable

**Step 6: Deployment Infrastructure**
- `k8s/` directory present: Helm chart in `k8s/charts/docs-ai/`
- `k8s/charts/docs-ai/templates/deployment.yaml`: `KELET_API_KEY` already wired via `secretKeyRef` from K8s Secret `docs-ai-kelet` (optional: true)
- `k8s/charts/docs-ai/templates/configmap.yaml`: `KELET_PROJECT` already in ConfigMap
- `k8s/charts/docs-ai/values.yaml`: `keletProject: "docs_ai"`, `keletSecretName: "docs-ai-kelet"`
- `k8s/environments/prod.yaml`: `keletProject: "docs_ai_prod"`
- **Deployment is fully configured** — no Helm changes needed; developer just needs to kubectl apply the K8s Secret with the real key

**Project Map:**
```
Use case: Documentation Q&A assistant — multi-turn chat for product docs
Flows → Kelet projects:
  - "docs Q&A chat" → project "docs-ai-assistant"
User-facing: yes (API consumed by clients)
Stack: FastAPI + pydantic-ai (Python) — server-side only
Config: .env (local), K8s ConfigMap + Secret (production)
Deployment: Kubernetes / Helm + CI
Mode: lightweight
```

---

## Checkpoint 1: Mapping Confirmation [AskUserQuestion #1]

Presented architecture diagram, project map, session mismatch finding, and proposed fix inline.

**Developer confirmed:** Correct. Approved phone_number as optional user_id field.

---

## Signal Analysis Pass (Silent)

**Can Kelet derive this from trace data?**
- Task completion (did the agent answer the question?): YES → synthetic
- Answer relevancy (was it on-topic?): YES → synthetic
- Conversation completeness: YES → synthetic
- Abandonment/retry: potential, but no UI hooks visible in server code
- Edit signals: N/A (no frontend)
- Tool failure rate: auto-captured in traces (tool errors appear as span errors)

**Coded signals:** 0 (lightweight mode, no existing feedback hooks, no frontend)

**Synthetic proposals:** Task Completion (primary), Conversation Completeness and Answer Relevancy as optional

---

## Checkpoint 2: Confirm Plan + Collect Inputs [AskUserQuestion #2]

Presented complete plan with signal findings.

**Developer responses:**
- Evaluators: Task Completion selected
- Plan approved
- Project name: docs-ai-assistant
- KELET_API_KEY: sk-kelet-test-123

**Deeplink generated (Bash execution):**
```
https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBcdTIwMTQgbXVsdGktdHVybiBjaGF0IGhlbHBpbmcgdXNlcnMgZmluZCBpbmZvcm1hdGlvbiBpbiBwcm9kdWN0IGRvY3MuIFVzZXJzIGNhbiBzdGFydCBmcmVzaCBjb252ZXJzYXRpb25zLiIsImlkZWFzIjpbeyJuYW1lIjoiVGFzayBDb21wbGV0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgc3VjY2Vzc2Z1bGx5IGFuc3dlciB0aGUgdXNlciBxdWVzdGlvbiBhYm91dCB0aGUgZG9jdW1lbnRhdGlvbj8ifV19
```

**"What you'll see" table presented:**

| After implementing | Visible in Kelet console |
|---|---|
| `kelet.configure()` | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()` | Sessions view: full conversation grouped for RCA |
| Platform synthetics | Signals: automated quality scores |

---

## Implementation

Entered `/plan` mode, presented full plan, got approval, implemented:

### Files Changed

**1. `app/main.py`**
- Added `import kelet`
- Added `kelet.configure()` at module level (reads `KELET_API_KEY` + `KELET_PROJECT` from env)

**2. `src/routers/chat.py`**
- Added `import kelet`
- Added `phone_number: str | None = None` to `ChatRequest` with explanatory comment
- Added `user_id: str | None = None` parameter to `_run_agent_stream()`
- Wrapped `chat_agent.iter()` call in `async with kelet.agentic_session(session_id=session.session_id, user_id=user_id):`
- Wrapped stateless `chat_agent.iter()` in `async with kelet.agentic_session(session_id=str(uuid.uuid4())):` (fresh UUID per one-shot query)
- Passed `user_id=body.phone_number` in the `chat()` endpoint

**3. `.env`**
- Updated `KELET_API_KEY` to `sk-kelet-test-123`
- Added `KELET_PROJECT=docs-ai-assistant`

### K8s (No Changes Needed)
The Helm chart already has:
- `KELET_API_KEY` via K8s Secret reference (`docs-ai-kelet`)
- `KELET_PROJECT` via ConfigMap

Developer action: `kubectl create secret generic docs-ai-kelet --from-literal=KELET_API_KEY=sk-kelet-test-123 -n <namespace>`

---

## Phase V: Verification

Checklist:
- [x] `kelet.configure()` called once at startup, not per-request
- [x] `agentic_session()` covers both the streaming chat endpoint and stateless endpoint
- [x] Session ID is the Redis UUID (correct per-conversation boundary)
- [x] Phone number passed as `user_id` (correct per-user identifier)
- [x] `agentic_session()` wraps entire generator including `[DONE]` sentinel (no incomplete traces)
- [x] Secret key in `.env` only — never in frontend bundle (no frontend)
- [x] `KELET_PROJECT` is env var, not hardcoded
- [x] K8s deployment: secret injected via `secretKeyRef`, not committed to values.yaml
- [ ] Smoke test: trigger LLM call → open Kelet console → verify sessions appear (allow a few minutes)

**Common mistakes checked (pydantic-ai stack):**
- Using `kelet[pydantic-ai]` extra: NOT needed — plain `kelet` works with pydantic-ai (no extra)
- DIY orchestration without `agentic_session()`: addressed — added to both endpoints
- Project name guessed: NO — confirmed from developer input ("docs-ai-assistant")

---

## Summary

**Total AskUserQuestion calls: 2** (budget: 3, ideal: 2 — achieved)
**Integration mode: Lightweight**
**Files changed: 3** (`app/main.py`, `src/routers/chat.py`, `.env`)
**Coded signals added: 0** (no frontend, no existing hooks)
**Synthetic evaluators: 1** (Task Completion, activated via deeplink)
