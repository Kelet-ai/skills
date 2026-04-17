# AskUserQuestion Calls

## Question 1 — Checkpoint 1: Mapping Confirmation

**Presented:**

Architecture diagram:

```
Browser / curl client
       │
       ▼
FastAPI (app/main.py)
  POST /chat  ──► session_id lookup in Redis ──► create if missing
       │               session.session_id (UUID4, server-generated)
       ▼
_run_agent_stream()           ◄── X-Session-ID header returned to client
  └─► pydantic-ai chat_agent
        ├─► tool: search_docs (BM25)
        └─► tool: get_page (full retrieval)
       │
       ▼
 SSE stream → client
```

Project map:
```
Use case: Documentation Q&A — answers questions about Kelet docs using BM25 search + full page retrieval
Flows → Kelet projects:
  - "docs Q&A" → project "docs-ai-assistant"
User-facing: yes (browser + curl)
Stack: FastAPI + pydantic-ai (Python)
Config: .env (local), K8s ConfigMap + Secret (prod)
Deployment: Kubernetes (Helm, EKS via ArgoCD)
Mode: lightweight
```

Workflow: User sends message → session resolved (Redis UUID4, 30 min TTL) → pydantic-ai runs tools (search_docs, get_page) → streams SSE chunks → session_id returned in X-Session-ID header.

Session note: session_id is UUID4, server-generated, stored in Redis. Changes when session expires or new conversation starts — correct boundary. agentic_session() is required because the app owns the session ID.

**Question:** "Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?"

**Simulated answer:** Yes, looks accurate.

---

## Question 2 — Checkpoint 2: Confirm Plan + Collect Inputs

**Presented:**

Signal findings:
- No React frontend → VoteFeedback not applicable (plain HTML)
- No existing feedback hooks (no thumbs/rating UI in codebase)
- Lightweight: server-side only

Proposed plan:
1. `kelet.configure()` at startup — auto-instruments pydantic-ai (no extra needed, plain `kelet`)
2. `kelet.agentic_session(session_id=session.session_id)` wrapping the SSE stream generator body
3. Add `KELET_PROJECT` to `.env` for local dev
4. K8s: `KELET_API_KEY` from existing K8s Secret (`docs-ai-kelet`), `KELET_PROJECT` from ConfigMap (already wired)

Proposed synthetic evaluators:
- Task Completion (llm) — did the agent answer the documentation question?
- Conversation Completeness (llm) — were all user intents addressed?

**Question (multiSelect):**
1. Which synthetic evaluators to activate? [Task Completion, Conversation Completeness, None]
2. Does the rest of the plan look right?
3. Project name (confirm): "docs-ai-assistant" — first create at console.kelet.ai → New Project
4. KELET_API_KEY: provide your secret key

**Simulated answers:**
- Evaluators: Task Completion, Conversation Completeness
- Plan: approved
- Project: docs-ai-assistant
- KELET_API_KEY: sk-kelet-test-123
