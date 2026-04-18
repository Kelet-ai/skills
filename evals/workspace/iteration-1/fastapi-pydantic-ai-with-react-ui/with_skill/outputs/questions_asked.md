# AskUserQuestion Calls

## Question 1 — Checkpoint 1: Mapping Confirmation

**Prompt shown to user:**

---
ANALYSIS · PROJECT + WORKFLOW MAPPING

Architecture:

```
Browser (React/Vite)
     |  POST /api/chat  (session_id in body)
     |  X-Session-ID header in response
     v
FastAPI (Fly.io)
     |  kelet.configure() at startup
     |  session resolved / created (Redis or in-memory)
     v
_run_agent_stream()
     |  kelet.agentic_session(session_id=...)
     v
pydantic-ai chat_agent
     |  search_docs tool (BM25)
     |  get_page tool
     v
LLM (AWS Bedrock / Claude)
```

Project Map:
  Use case: Docs Q&A assistant — answers user questions about product documentation
  Flows: 1 (POST /chat session + GET /chat stateless one-shot)
  User-facing: yes (React frontend, Vite)
  Stack: FastAPI + pydantic-ai (Python) + React (TypeScript)
  Config: .env
  Deployment: Vercel (frontend) + Fly.io (backend)
  Mode: lightweight

Session semantics: session_id is server-generated UUID, returned via X-Session-ID response header, stored in React state. Correct mapping — new session on first request, same ID reused for conversation continuity.

Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?
---

**Simulated answer:** Yes, that's accurate.

---

## Question 2 — Checkpoint 2: Confirm Plan + Collect Inputs

**Prompt shown to user:**

---
Signal Analysis findings:

- No existing feedback UI (no thumbs, ratings, edit fields) — need to add VoteFeedback
- Session ID flows cleanly: server generates it, returns in X-Session-ID header, React stores it in state → perfect hook for VoteFeedback.Root session_id prop
- pydantic-ai is auto-instrumented — no extras needed, plain `kelet` package

Proposed plan (lightweight):

BACKEND:
  1. Add `import kelet` + `kelet.configure()` to app/main.py at startup
  2. Wrap _run_agent_stream body with `kelet.agentic_session(session_id=session.session_id)` in src/routers/chat.py

FRONTEND:
  3. Add @kelet-ai/feedback-ui to package.json (already included in evaluation setup)
  4. Wrap app in KeletProvider in main.tsx (VITE_KELET_PUBLISHABLE_KEY + VITE_KELET_PROJECT)
  5. Add VoteFeedback.Root next to each assistant message in App.tsx, passing sessionId from X-Session-ID header

SYNTHETICS (zero code — platform-managed):
  Please select which evaluators to activate:

  [ ] Task Completion — Did the agent successfully answer the user's documentation question?
  [ ] Sentiment Analysis — Is the user expressing frustration or repeated corrections?
  [ ] Conversation Completeness — Were any user intents left unaddressed?
  [ ] None

ENV:
  KELET_API_KEY (sk-kelet-...) — server only, written to .env
  VITE_KELET_PUBLISHABLE_KEY (pk-kelet-...) — frontend, written to .env
  Project name: create first at console.kelet.ai → top-nav → New Project, must match exactly

Does the plan look right? Please also provide:
  - KELET_API_KEY
  - VITE_KELET_PUBLISHABLE_KEY
  - Project name (confirm or correct: "docs-ai-assistant")
---

**Simulated answers:**
  - Evaluators selected: Task Completion, Sentiment Analysis
  - Plan approval: yes
  - KELET_API_KEY: sk-kelet-test-123
  - VITE_KELET_PUBLISHABLE_KEY: pk-kelet-test-456
  - Project name: docs-ai-assistant
