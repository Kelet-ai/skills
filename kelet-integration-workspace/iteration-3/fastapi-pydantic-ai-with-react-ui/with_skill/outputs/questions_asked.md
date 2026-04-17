# Questions Asked

## Question 1 — Checkpoint 1: Mapping Confirmation

**Presented to user:**

```
🔍  ANALYSIS · PROJECT + WORKFLOW MAPPING

Architecture:
  React (Vite) ─── /api/chat POST ─── FastAPI ─── pydantic-ai agent ─── LLM
      |                                   |
  sessionId state               X-Session-ID header
  (stored in useState)         (server-generated UUID)

Use case: Documentation AI assistant — answers questions using docs knowledge base
Flows → Kelet projects:
  - chat flow → project "docs-ai-assistant"
User-facing: yes (React Vite frontend)
Stack: FastAPI + pydantic-ai
Config: .env (KELET_API_KEY + KELET_PROJECT already present)
Deployment: app description says Vercel (frontend) + Fly.io (backend); infra scan found k8s/helm charts (prod)
Mode: lightweight — kelet already in deps, configure() + agentic_session() already in place

Session ID: server-generated UUID, returned in X-Session-ID header, captured in React state.
Semantics: correct — new session created when session_id is absent or expired.

Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?
```

**Simulated response:** Yes, accurate.

---

## Question 2 — Checkpoint 2: Plan Confirmation + Keys

**Presented to user:**

```
📍  Analysis ✅ → Batch 1 ✅ → Signal Analysis 🔄 → Batch 2 ○ → impl ○

Signal findings:
- No existing feedback hooks in the UI
- pydantic-ai is a supported framework; sessions auto-inferred (but session_id is server-owned → agentic_session() required to link)
- No copy/retry/edit buttons to wire signals to
- One coded signal: VoteFeedback on assistant messages

Proposed plan (lightweight):
1. Backend: already done (kelet.configure() + agentic_session() in place)
2. Frontend — main.tsx: add KeletProvider wrapping App
3. Frontend — App.tsx: add VoteFeedback.Root/UpvoteButton/DownvoteButton/Popover on each assistant message, session_id from X-Session-ID header
4. Synthetics deeplink (no code) — platform evaluators

Select which synthetic evaluators to activate:
[x] Task Completion — did the assistant answer the question?
[x] Sentiment Analysis — user frustration/dissatisfaction
[ ] Conversation Completeness
[ ] Answer Relevancy
[ ] None

Does the rest of the plan look right?
Project name: docs-ai-assistant (create first at console.kelet.ai → top-nav → New Project if not done)
KELET_API_KEY: already in .env ✓
VITE_KELET_PUBLISHABLE_KEY: already in .env ✓
```

**Simulated response:**
- Evaluators selected: Task Completion + Sentiment Analysis
- Plan approved
- project="docs-ai-assistant", KELET_API_KEY="sk-kelet-test-123", VITE_KELET_PUBLISHABLE_KEY="pk-kelet-test-456"
