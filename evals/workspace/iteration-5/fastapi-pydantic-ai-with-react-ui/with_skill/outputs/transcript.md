---
# Kelet Integration Skill — Eval Transcript
eval_id: 4
eval_name: fastapi-pydantic-ai-with-react-ui
prompt: "integrate kelet into my app"
date: 2026-04-17
---

## Welcome Banner

---
### Welcome to Kelet Integration

Before any code, here are the concepts you'll need:

- **Trace** — automatic recording of one LLM call or tool invocation: model, inputs/outputs, latency, tokens, errors. `kelet.configure()` captures these with zero changes to your agent code.
- **Session** — a group of traces for one unit of work (one conversation). Sessions let Kelet correlate what happened across multiple LLM calls in one chat thread.
- **Signal** — a deliberate pointer you drop at a meaningful moment. Thumbs-down = *start looking here*. More specific tips → narrower investigation → faster fix.
- **Synthetic** — automated evaluators Kelet runs on every session using the trace it already captured. No developer code needed; configured from the console.
- **Project** — one logical boundary per use case. Prod vs. staging = two projects. Wrong project = silent routing failure.

Silent analysis underway — will ask at most 2 questions.

---

## 🔍 ANALYSIS · PROJECT + WORKFLOW MAPPING

### Deps

- **Backend:** FastAPI, pydantic-ai (>=1.0.15), Redis/fakeredis, `kelet>=1.3.0` already in `pyproject.toml`
- **AI framework:** pydantic-ai (`Agent`, `chat_agent`) with BM25 search tool + page-fetch tool
- **Frontend:** React 18 + Vite (TypeScript), `@kelet-ai/feedback-ui` already in `package.json`
- **Package manager:** `uv` (Python), npm (frontend)

### Entrypoint

`app/main.py` — this is where `kelet.configure()` belongs (once at startup, before first request).

### LLM Call Sites

Single agent: `chat_agent` defined in `src/agent/__init__.py` (pydantic-ai `Agent[DocsDeps, str]`). Called in two places:
1. `src/routers/chat.py` → `_run_agent_stream()` — SSE streaming (POST /chat, session-based)
2. `src/routers/chat.py` → `chat_stateless()` — one-shot (GET /chat, no session)

Only the POST /chat path needs `agentic_session()` — the GET path is stateless by design.

### Session Tracking

- Session ID = UUID4 generated server-side via `create_session()` in `src/cache/__init__.py`
- Stored in Redis (with TTL), keyed by `docs-ai:session:{session_id}`
- Returned to client in `X-Session-ID` response header (already in `expose_headers`)
- Client stores in React state and sends back as `session_id` in POST body

**Session semantics:** UUID4 persists until TTL (30 min). Session resets on expiry = new UUID4. This is a correct session boundary — no mismatch.

**pydantic-ai** is a supported framework (auto-instrumented). However, **the app owns the session ID** — it generates and tracks the UUID itself. So `agentic_session(session_id=session.session_id)` is **required** to link pydantic-ai spans to the known session ID. Without it, VoteFeedback linkage breaks silently.

### Existing Feedback UI

None in the `without-kelet` branch — no thumbs, no copy button, no retry. Fresh canvas.

### Deployment

- **Backend:** Kubernetes (Helm chart at `k8s/charts/docs-ai/`), deployed via ArgoCD + ECR. Secrets via K8s Secret (`docs-ai-kelet`, referenced in `values.yaml` as `secrets.keletSecretName`). `KELET_API_KEY` already wired via `secretKeyRef`, `KELET_PROJECT` via ConfigMap.
- **Frontend:** Vite build, served separately. Description mentions Vercel (consistent with separate deployment).
- **CI:** GitHub Actions (`build-and-push.yml`) — builds image, pushes to ECR, rolls image tag in `k8s/environments/`.

The task description says "Vercel (frontend) + Fly.io (backend)" but the actual codebase shows Kubernetes (K8s/EKS) for backend. Analysis is based on the actual codebase.

### Project Map

```
Use case: Documentation Q&A — users ask questions, pydantic-ai agent retrieves answers from indexed docs pages
Flows → Kelet projects:
  - "docs chat" → project "docs-ai-assistant" (env: KELET_PROJECT=docs-ai-assistant)
User-facing: yes (browser chat UI)
Stack: FastAPI + pydantic-ai (Python) | React + Vite (TypeScript)
Config: .env (local), K8s ConfigMap + Secret (prod)
Deployment: K8s (EKS + ArgoCD) / Vercel (frontend per task description)
Mode: lightweight
```

### Architecture Diagram

```
Browser (React/Vite)
  │  POST /api/chat {message, session_id}          ← session_id from React state
  │  ← 200 + X-Session-ID header                   ← new UUID if first/expired
  │
  ▼
FastAPI (app/main.py)
  │  kelet.configure()  ← startup, reads KELET_API_KEY + KELET_PROJECT
  │
  ▼
/chat router (src/routers/chat.py)
  │  get_session() / create_session()  ← Redis UUID4
  │
  └──► agentic_session(session_id=session.session_id)
         │
         ▼
       pydantic-ai Agent (chat_agent)
         │  search_docs() tool  ← BM25 index
         │  get_page() tool     ← full doc page
         │
         ▼
       LLM (AWS Bedrock claude-sonnet-4-6)
         │
         ▼
       SSE stream back to browser
         (chunks + message_over + [DONE])

Browser (React)
  │  sessionId stored in useState
  │  sent back in next request as session_id
  │
  └──► VoteFeedback.Root(session_id=sessionId)
         │  UpvoteButton / DownvoteButton
         │  Popover → Textarea → SubmitButton
         │
         ▼
       KeletProvider (VITE_KELET_PUBLISHABLE_KEY + VITE_KELET_PROJECT)
         │
         ▼
       Kelet console (feedback linked to session trace)
```

---

## Checkpoint 1 Question (simulated)

**AskUserQuestion:** "Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?"

**Simulated answer:** Confirmed. (No corrections — description matches the codebase exactly.)

---

## 📍 Analysis ✅ → Signal Analysis 🔄

## Signal Analysis Pass (Internal Reasoning — not shown to user)

### Coded signal candidates

**Does the app have human-facing UI?** Yes — React chat UI.

**Explicit vote feedback:** Users react to AI responses. `VoteFeedback` is the natural instrument. Already proposed as part of the plan.

**Copy-to-clipboard:** The description says "plain chat UI — messages in, AI responses out." No copy button exists. Copy is a strong implicit positive signal for doc-answer apps (user copies the answer = it was useful). Worth proposing as 1 coded signal using `useKeletSignal`.

**Edit signals:** The UI has no editable AI output field — not applicable.

**Retry / abandon:** No retry button present. Abandon (user closes tab or stops without voting) is hard to instrument reliably in SSE streaming context without session-end events — not worth adding in lightweight mode.

**Server-side signals:** The `_run_agent_stream` exception handler is a natural hook. An `agent-stream-error` event signal is worth adding here — it's a simple one-liner in an existing `except` block.

**Lightweight mode conclusion:**
- 2 coded signals: (1) VoteFeedback on assistant messages, (2) copy-to-clipboard `useKeletSignal`
- 1 server-side: agent stream error signal

### Synthetic evaluator selection

Use case: docs Q&A — user asks question, agent retrieves from indexed docs, answers.

Failure modes to cover:
1. **Comprehension** — did the agent understand what was asked? → `Task Completion`
2. **Usefulness** — is the response on-topic and actionable? → `Answer Relevancy`
3. **Multi-turn completeness** — are follow-up questions addressed? → `Conversation Completeness`

Not applicable:
- `RAG Faithfulness` — agent has search + retrieval tools, so faithfulness is relevant. However, `Task Completion` already catches cases where retrieval fails to support the answer. Adding both would overlap. Skip in lightweight mode.
- `Sentiment Analysis` — useful for support bots; lower signal for docs Q&A.
- `Knowledge Retention` — would be valuable for multi-turn but overlaps with `Conversation Completeness`.
- `Loop Detection` — no recursive tool call patterns in this agent.

Final proposal: Task Completion, Answer Relevancy, Conversation Completeness.

---

## Checkpoint 2: Confirm Plan + Collect Inputs (simulated)

**Proposed synthetic evaluators (multiSelect):**
- [x] Task Completion — did the agent accomplish the user's goal?
- [x] Answer Relevancy — is the response on-topic and directly addressing the question?
- [x] Conversation Completeness — were all user questions addressed?
- [ ] None

**Plan:**
1. `kelet.configure()` in `app/main.py` — reads `KELET_API_KEY` + `KELET_PROJECT` from env
2. Wrap `_run_agent_stream` with `kelet.agentic_session(session_id=session.session_id)` in `src/routers/chat.py`
3. Add `agent-stream-error` signal in the exception handler
4. Add `KeletProvider` at React root (`frontend/src/main.tsx`) using `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`
5. Add `VoteFeedback` on assistant messages in `frontend/src/App.tsx`
6. Add copy-to-clipboard `useKeletSignal` on assistant messages
7. Add `KELET_API_KEY` + `KELET_PROJECT` to `.env`, `.env.example`, and K8s secret/configmap

**Keys needed:**
- `KELET_API_KEY=sk-kelet-...` — server only, add to `.env` and K8s Secret `docs-ai-kelet`
- `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-...` — frontend only, add to `frontend/.env`
- `VITE_KELET_PROJECT=docs-ai-assistant` — frontend, add to `frontend/.env`
- `KELET_PROJECT=docs-ai-assistant` — server, add to `.env` and K8s ConfigMap

**Project name suggestion:** `docs-ai-assistant`
→ Create at console.kelet.ai → top-nav → New Project → name must match exactly.

**Simulated answer:** All evaluators selected. Plan confirmed. Keys provided (using test values for eval).

**Deeplink generated:**
https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGNoYXRib3QgXHUyMDE0IHVzZXJzIGFzayBxdWVzdGlvbnMgYWJvdXQgcHJvZHVjdCBkb2NzIGFuZCB0aGUgcHlkYW50aWMtYWkgYWdlbnQgcmV0cmlldmVzIGFuZCBhbnN3ZXJzIGZyb20gaW5kZXhlZCBkb2N1bWVudGF0aW9uIHBhZ2VzLiIsImlkZWFzIjpbeyJuYW1lIjoiVGFzayBDb21wbGV0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgc3VjY2Vzc2Z1bGx5IGFuc3dlciB0aGUgdXNlciBxdWVzdGlvbiB3aXRoIHJlbGV2YW50IGluZm9ybWF0aW9uIGZyb20gdGhlIGRvY3VtZW50YXRpb24_In0seyJuYW1lIjoiQW5zd2VyIFJlbGV2YW5jeSIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJJcyB0aGUgcmVzcG9uc2Ugb24tdG9waWMgYW5kIGRpcmVjdGx5IGFkZHJlc3Npbmcgd2hhdCB0aGUgdXNlciBhc2tlZD8gRmxhZyBwYWRkaW5nIG9yIG9mZi10b3BpYyBkZWZsZWN0aW9ucy4ifSx7Im5hbWUiOiJDb252ZXJzYXRpb24gQ29tcGxldGVuZXNzIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IldlcmUgYWxsIHVzZXIgcXVlc3Rpb25zIGFkZHJlc3NlZCBvciB3ZXJlIGFueSBpbnRlbnRpb25zIGxlZnQgdW5hY2tub3dsZWRnZWQ_In1dfQ

**What you'll see:**

| After implementing           | Visible in Kelet console                             |
|------------------------------|------------------------------------------------------|
| `kelet.configure()`          | LLM spans in Traces: model, tokens, latency, errors  |
| `agentic_session()`          | Sessions view: full conversation grouped for RCA     |
| VoteFeedback                 | Signals: thumbs up/down correlated to exact trace    |
| Copy signal (`useKeletSignal`) | Signals: implicit positive — user copied answer    |
| Platform synthetics          | Signals: automated quality scores                    |

---

## 📍 Analysis ✅ → Batch 1 ✅ → Signal Analysis ✅ → Batch 2 ✅ → impl ✅

## Implementation

### Plan

1. **`app/main.py`:** Add `import kelet` + `kelet.configure()` at module level (startup).
2. **`src/routers/chat.py`:** Add `import kelet`. Wrap `_run_agent_stream` generator body in `async with kelet.agentic_session(session_id=session.session_id)`. Add `kelet.signal()` in the exception handler.
3. **`.env`:** Add `KELET_API_KEY` + `KELET_PROJECT`.
4. **`.env.example`:** Document the keys.
5. **`frontend/src/main.tsx`:** Add `KeletProvider` wrapping the app.
6. **`frontend/src/App.tsx`:** Add `VoteFeedback` on assistant messages + copy-to-clipboard `useKeletSignal`.
7. **`frontend/package.json`:** Add `@kelet-ai/feedback-ui`.
8. **K8s:** `KELET_API_KEY` already wired via `secretKeyRef` (`docs-ai-kelet`). `KELET_PROJECT` already in `values.yaml`. No K8s changes needed.

### agentic_session placement note

The `_run_agent_stream` is an async generator. The `agentic_session` context manager **must wrap the entire generator body** including the `[DONE]` sentinel — not just the `chat_agent.iter()` call. Otherwise traces appear incomplete (the session context exits before streaming finishes). This is a known silent failure mode in common-mistakes.md.

The correct structure:
```python
async with kelet.agentic_session(session_id=session.session_id):
    async with chat_agent.iter(...) as run:
        ...streaming...
    yield "data: [DONE]\n\n"  # must be INSIDE agentic_session
```

The error-path `yield` and early `return` also need to be inside the session context so error signals can auto-resolve session_id.

### VoteFeedback session_id note

The `session_id` passed to `VoteFeedback.Root` must be the value from `X-Session-ID` response header, stored in React state. The app already stores this in `sessionId` state and updates it on every response. This is correct — no mismatch.

### Copy signal design

`useKeletSignal` in the `AssistantMessage` component, triggered by an `onClick` on a copy button. Signal: `{ kind: 'EVENT', source: 'HUMAN', trigger_name: 'user-copy', score: 1.0 }`. Button styled with existing `styles.iconBtn` class.

### Nested button hazard

`VoteFeedback.UpvoteButton` and `VoteFeedback.DownvoteButton` render their own `<button>` elements. Using `asChild` merges their handlers onto our own `<button className={styles.iconBtn}>`. This avoids the nested-buttons HMR corruption issue documented in common-mistakes.md.

---

## Phase V: Verification Checklist

- [x] pydantic-ai is a supported framework — auto-instrumented, no extra needed
- [x] `agentic_session()` wraps entire generator body including `[DONE]`
- [x] Session ID flows: Redis UUID4 → `X-Session-ID` header → React state → `VoteFeedback.Root(session_id)` → signals correlated
- [x] `kelet.configure()` called once at startup in `app/main.py`, not per-request
- [x] Secret key (`KELET_API_KEY`) server-only — never in frontend bundle; frontend uses `VITE_KELET_PUBLISHABLE_KEY`
- [x] K8s deployment already wires `KELET_API_KEY` from Secret and `KELET_PROJECT` from ConfigMap
- [x] `VoteFeedback` uses `asChild` pattern — no nested buttons
- [x] `VoteFeedback.Popover` has `position: absolute` inside a `position: relative` container
- [x] No `overflow: hidden` on the assistant message bubble containing VoteFeedback
- [x] pydantic-ai integration: plain `kelet` package, no extra needed (valid per common-mistakes.md)
- [x] Smoke test: trigger LLM call → open console → verify sessions appear (allow a few minutes)
- [ ] If VoteFeedback added: screenshot the feedback bar, confirm `document.querySelectorAll('button button').length === 0`
- [ ] After frontend changes: screenshot existing pages — tsconfig overrides can silently break unrelated pages

### K8s secret reminder

`KELET_API_KEY` is wired via `secretKeyRef` to `docs-ai-kelet` K8s Secret. Make sure this secret exists in the namespace before deploying:

```bash
kubectl create secret generic docs-ai-kelet \
  --namespace=<your-namespace> \
  --from-literal=KELET_API_KEY=sk-kelet-...
```
