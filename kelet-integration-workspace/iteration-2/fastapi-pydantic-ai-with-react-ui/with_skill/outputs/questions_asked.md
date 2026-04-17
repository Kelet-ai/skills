# AskUserQuestion Calls

## Slot 1 — Checkpoint 1: Mapping Confirmation

**Question presented to developer:**

"Here's what I found in your codebase:

**Architecture:**
```
Browser (React/Vite)
  │
  ├─ POST /api/chat  ──────────────────────────────────────────►  FastAPI /chat
  │   body: { message, session_id }                               │
  │                                                               ├─ Redis session lookup / create
  │                                                               ├─ kelet.agentic_session(session_id=...)
  │                                                               │   └─ chat_agent.iter()
  │                                                               │       ├─ search_docs (BM25 retrieval)
  │                                                               │       └─ get_page (page content)
  │                                                               └─ SSE stream + X-Session-ID header
  │
  ◄── SSE chunks + X-Session-ID header ───────────────────────────
  │
  └─ React state: sessionId → VoteFeedback
```

**Project map:**
- Use case: Documentation Q&A — pydantic-ai agent with search_docs + get_page tools
- Single flow → project "docs-ai-assistant" (suggested)
- Server-generated session IDs (UUID per conversation, stored in Redis)
- Deployment: Vercel (frontend) + Fly.io (backend)

**Session note:** Session IDs are server-generated UUIDs per conversation — `agentic_session(session_id=...)` is required to link VoteFeedback signals to traces.

Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?"

**Simulated answer:** Yes, looks right. The frontend also has a Send button and input. No existing feedback buttons at all.

---

## Slot 2 — Checkpoint 2: Confirm Plan + Collect Inputs

**Question presented to developer:**

"Here's the integration plan:

**Signal analysis:**
- No existing feedback UI (no thumbs, no copy, no retry buttons)
- React UI scan: found opportunity for copy-to-clipboard signal (useKeletSignal — 1 new Copy button next to AI messages)
- No edit inputs on AI output (no useFeedbackState applicable)

**Proposed plan:**
1. Backend: `kelet.configure()` at startup + `kelet.agentic_session(session_id=...)` wrapping agent.iter()
2. Frontend: `KeletProvider` at root + `VoteFeedback` next to AI messages + `useKeletSignal` for copy
3. Env: `KELET_API_KEY` + `KELET_PROJECT` + `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`

**1. Which synthetic evaluators should Kelet run automatically on every session?** (select all that apply)
  - [x] Task Completion — Did the agent fully answer the user's documentation question?
  - [x] Sentiment Analysis — User frustration, repeated corrections, dissatisfaction throughout the session
  - [ ] Conversation Completeness — User intentions left unaddressed or deflected
  - [ ] Answer Relevancy — Off-topic responses, padding, missed the actual question
  - [ ] None

**2. Does the rest of the plan look right?**

**3. Keys + project name:**
  - `KELET_API_KEY` (sk-kelet-...): Get at console.kelet.ai/api-keys
  - `VITE_KELET_PUBLISHABLE_KEY` (pk-kelet-...): Frontend publishable key
  - Project name: Create first at console.kelet.ai → top-nav → New Project (must match exactly — wrong name = silent routing failure)"

**Simulated answers:**
- Evaluators selected: Task Completion + Sentiment Analysis
- Plan approval: Yes, looks good
- KELET_API_KEY: sk-kelet-test-123
- VITE_KELET_PUBLISHABLE_KEY: pk-kelet-test-456
- Project name: docs-ai-assistant

---

## Budget Summary

- **Slots used:** 2 of 3 (ideal: 2)
- **Slot 3:** Not needed — deployment identified (Vercel + Fly.io) from task description; secrets handled safely
