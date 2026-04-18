# Integration Transcript

## App Description

FastAPI backend + pydantic-ai agent. React frontend (Vite). Plain chat UI — messages in, AI responses out. No feedback buttons at all. Session ID generated server-side, returned in X-Session-ID response header, stored in React state. Deployed on Vercel (frontend) + Fly.io (backend).

---

## Welcome

══════════════════════════════════════════════════
Welcome to Kelet Integration
══════════════════════════════════════════════════

**Kelet is an AI detective for your AI app failures** — not a dashboard, but a reasoning agent that investigates root causes and suggests fixes.

**The detective model:** Kelet sees two kinds of evidence:

- **Traces** — automatic recordings of every LLM call, tool use, latency, error. No code needed for these.
- **Signals** — tips you drop at meaningful moments. A thumbs-down means *start looking here*, not *this session failed*. A copy event says *user found value*. An abandon says *user gave up*. More deliberate tips = narrower investigation = faster fix.

*"Signals are tips. Traces are the scene. Kelet follows the evidence."*

**What we'll do:** 6 phases. I'll do the work, you confirm each step.

---

## Phase 0a: Project Mapping

══════════════════════════════════════════════════
PHASE 0a · PROJECT MAPPING
══════════════════════════════════════════════════

> 🧠 Mapping the codebase first — Kelet auto-instruments your framework, but only once it knows which project to route data to and where session IDs live.

### Files Read

- `pyproject.toml` — dependencies: fastapi, pydantic-ai, kelet>=1.3.0, redis, fakeredis
- `frontend/package.json` — dependencies: react, @kelet-ai/feedback-ui
- `app/main.py` — FastAPI entrypoint, lifespan, CORS config
- `src/routers/chat.py` — POST /chat (SSE session) and GET /chat (stateless), session management
- `src/agent/__init__.py` — pydantic-ai Agent, DocsDeps, search_docs and get_page tools
- `src/settings/__init__.py` — Pydantic Settings, reads from .env
- `frontend/src/App.tsx` — plain chat UI, no feedback buttons
- `frontend/src/main.tsx` — React root
- `frontend/vite.config.ts` — Vite config with /api proxy

### Key Findings

1. **pydantic-ai detected** — auto-instrumented by kelet. Sessions inferred structurally but NOT by session ID (app owns the UUID, pydantic-ai doesn't know it). `agentic_session()` is required.

2. **Session ID**: server-generates a UUID per conversation in `create_session()` → returns it as `X-Session-ID` response header → frontend captures via `res.headers.get('X-Session-ID')` and stores in React state. Session boundary is correct: new UUID per conversation, same ID across turns within a session. ✅ This is a proper session boundary.

3. **CORS**: `expose_headers=["X-Session-ID"]` already present — browser can read this header from cross-origin requests. Critical for VoteFeedback session_id propagation.

4. **Two agentic entry points**: `_run_agent_stream()` (POST /chat — multi-turn sessions) and `chat_stateless()` (GET /chat — one-shot queries). Both need `agentic_session()`.

5. **Deployment**: Vercel (frontend) + Fly.io (backend). `fly secrets set KELET_API_KEY=...` for backend; Vercel dashboard env vars for frontend.

6. **No feedback UI**: App.tsx renders plain text messages with no buttons. VoteFeedback must be added from scratch.

### Architecture Diagram

```
Browser (React/Vite — Vercel)
  │
  │  POST /api/chat  { message, session_id }
  │  <── X-Session-ID response header
  │
  ▼
FastAPI (Fly.io)
  [kelet.configure() at startup]
  │
  │  session lookup/create (Redis / in-memory)
  ▼
_run_agent_stream()
  [kelet.agentic_session(session_id=session.session_id)]
  │
  ▼
pydantic-ai chat_agent
  ├── search_docs tool (BM25)
  └── get_page tool (content fetcher)
  │
  ▼
LLM (AWS Bedrock / Claude Sonnet)
  │
  ▼
SSE stream → browser (chunks + message_over events)
```

### Project Map

```
Use case: Documentation Q&A — answers user questions about product docs using pydantic-ai agent
Flows: 1 (single chat flow — POST /chat session + GET /chat stateless)
User-facing: yes (React/Vite frontend)
Stack: FastAPI + pydantic-ai (Python) + React (TypeScript/Vite)
Config: .env
Deployment: Vercel (frontend) + Fly.io (backend)
```

╔══════════════════════════════════╗
║  ✅  Phase 0a complete           ║
╚══════════════════════════════════╝

📍  0a ✅ → 0b ○ → 0c ○ → 0d ○ → 1 ○ → impl ○

**[AskUserQuestion]** "Does this diagram and map accurately represent your system? Anything I missed?"

**[Developer response]** "Yes, looks right."

---

## Phase 0b: Agentic Workflow + UX Mapping

══════════════════════════════════════════════════
PHASE 0b · WORKFLOW & UX MAPPING
══════════════════════════════════════════════════

> 🧠 Mapping failure modes before proposing signals — every failure mode here becomes a signal candidate in 0c. Signals without a failure map are guesses.

### Workflow

1. User sends a question via POST /chat with optional `session_id` and `current_page_slug`
2. Server resolves or creates a Redis session (30-min TTL)
3. `chat_agent` is invoked with the question + message history
4. Agent decides whether to call `search_docs` (BM25 search) and/or `get_page` (full content retrieval)
5. LLM generates answer from retrieved content and conversation history
6. Response streamed back as SSE chunks + `message_over` events

**Decision points where things go wrong:**
- `search_docs` returns nothing relevant → agent hallucinates or says "I don't know"
- `get_page` called with wrong slug → "Page not found" returned, agent invents content
- LLM answers from training data instead of retrieved docs → confidently wrong
- Multi-turn: agent loses context from earlier turns (history truncated or confused)
- Session TTL expires mid-conversation → user loses context, gets confused

**Success looks like:** Agent retrieves the right page/section and directly answers the question in 1–2 tool calls.

**Failure looks like:** Agent returns generic answer, "I couldn't find that", or factually wrong answer; user rephrases and tries again.

### UX

- What's shown: plain text AI responses (no structured output, no code blocks by design, no citations)
- Where users react: currently nowhere — no feedback buttons, no copy button, no retry button
- Implicit dissatisfaction signals: close the tab, rephrase the question, send another message immediately after getting a response

╔══════════════════════════════════╗
║  ✅  Phase 0b complete           ║
╚══════════════════════════════════╝

📍  0a ✅ → 0b ✅ → 0c ○ → 0d ○ → 1 ○ → impl ○

**[AskUserQuestion]** "Does this workflow and failure map look right? Anything to add or correct?"

**[Developer response]** "Looks good."

---

## Phase 0c: Signal Brainstorming

══════════════════════════════════════════════════
PHASE 0c · SIGNAL BRAINSTORMING
══════════════════════════════════════════════════

> 🧠 Choosing where to drop the tips. Signals aren't pass/fail verdicts — they're directional cues pointing Kelet's investigation.

### Proposed Signals

**1. Explicit — VoteFeedback (thumbs up/down)**
No existing feedback UI → add `VoteFeedback` next to each assistant message. This is the highest-value signal: direct user judgment on the response that generated the trace. A downvote tells Kelet exactly which session to start with.

**2. Coded — Copy to clipboard (`user-copy`)**
Docs Q&A: users often copy snippets to paste into their work. A copy event signals "I got value from this response." Contrasted against downvotes, it gives Kelet a richer picture — high copy + low downvote = healthy session. Location: copy button in AssistantMessage, `useKeletSignal()`.

**3. Coded — Session abandon (`user-abandon`)**
User closes the tab while a session is active and has messages → they didn't get what they needed. `window.beforeunload` event with `score: 0.0`. Strong implicit dissatisfaction. Location: `useEffect` in App component.

**4. Synthetic — Task Completion**
Did the agent successfully answer the documentation question? Catches deflection ("I'm not sure about that"), hallucinates a missing page, or fails to find the relevant content. LLM-type — requires reading the answer to judge it. One evaluator for the "Usefulness" failure category.

**5. Synthetic — Sentiment Analysis**
Is the user expressing frustration, corrections, or dissatisfaction across turns? Catches patterns like repeated rephrasing or "that's not what I asked." LLM-type. One evaluator for the "User reaction" failure category.

**6. Synthetic — RAG Faithfulness**
Are the agent's answers faithful to the retrieved documentation content? The app uses BM25 retrieval — the retrieved content is in the trace. Kelet can compare what was retrieved vs. what was claimed. One evaluator for the "Correctness" failure category.

**[AskUserQuestion — multiSelect]** "Which explicit and coded signals should I implement?"
- VoteFeedback (thumbs up/down) on each AI response
- Copy-to-clipboard signal (user-copy)
- Session abandon signal (user-abandon)

**[Developer response]** All three selected.

**[AskUserQuestion — multiSelect]** "Which synthetic evaluators should Kelet run automatically?"
- Task Completion — did the agent answer the question?
- Sentiment Analysis — is the user expressing frustration?
- RAG Faithfulness — are answers faithful to retrieved docs?

**[Developer response]** All three selected.

**[Bash — deeplink generation]:**

> **Action required → click this link to activate your synthetic evaluators:**
> https://console.kelet.ai/docs_ai_prod/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBcdTIwMTQgdXNlciBhc2tzIHF1ZXN0aW9ucyBhYm91dCBwcm9kdWN0IGRvY3MsIHB5ZGFudGljLWFpIGFnZW50IHJldHJpZXZlcyBhbmQgYW5zd2VycyB1c2luZyBzZWFyY2hfZG9jcyBhbmQgZ2V0X3BhZ2UgdG9vbHMiLCJpZGVhcyI6W3sibmFtZSI6IlRhc2sgQ29tcGxldGlvbiIsImV2YWx1YXRvcl90eXBlIjoibGxtIiwiZGVzY3JpcHRpb24iOiJEaWQgdGhlIGFnZW50IHN1Y2Nlc3NmdWxseSBhbnN3ZXIgdGhlIHVzZXIncyBkb2N1bWVudGF0aW9uIHF1ZXN0aW9uLCBvciBkaWQgaXQgZGVmbGVjdCwgaGFsbHVjaW5hdGUgYSBtaXNzaW5nIHBhZ2UsIG9yIGZhaWwgdG8gZmluZCB0aGUgcmVsZXZhbnQgY29udGVudD8ifSx7Im5hbWUiOiJTZW50aW1lbnQgQW5hbHlzaXMiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiSXMgdGhlIHVzZXIgZXhwcmVzc2luZyBmcnVzdHJhdGlvbiwgY29ycmVjdGlvbnMsIG9yIGRpc3NhdGlzZmFjdGlvbiBhY3Jvc3MgdHVybnM_IENhdGNoZXMgcGF0dGVybnMgbGlrZSByZXBlYXRlZCByZXBocmFzaW5nIG9yIGV4cGxpY2l0IGNvcnJlY3Rpb25zLiJ9LHsibmFtZSI6IlJBRyBGYWl0aGZ1bG5lc3MiLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiQXJlIHRoZSBhZ2VudCdzIGFuc3dlcnMgZmFpdGhmdWwgdG8gdGhlIHJldHJpZXZlZCBkb2N1bWVudGF0aW9uIGNvbnRlbnQsIG9yIGRvZXMgaXQgbWFrZSBjbGFpbXMgbm90IHN1cHBvcnRlZCBieSB0aGUgcmV0cmlldmVkIHBhZ2VzPyJ9XX0
>
> This will generate evaluators for: **Task Completion**, **Sentiment Analysis**, **RAG Faithfulness** in project **docs_ai_prod**. Click "Activate All" once you've reviewed them.

**[AskUserQuestion]** "Have you clicked the link and activated the evaluators?"

**[Developer response]** "Yes, activated."

╔══════════════════════════════════╗
║  ✅  Phase 0c complete           ║
╚══════════════════════════════════╝

📍  0a ✅ → 0b ✅ → 0c ✅ → 0d ○ → 1 ○ → impl ○

---

## Phase 0d: What You'll See in Kelet

══════════════════════════════════════════════════
PHASE 0d · WHAT YOU'LL SEE
══════════════════════════════════════════════════

> 🧠 Previewing the console before writing code — so every implementation step has a visible target.

| After implementing          | Visible in Kelet console                                                         |
|-----------------------------|----------------------------------------------------------------------------------|
| `kelet.configure()`         | LLM spans in Traces: model, tokens, latency, search_docs/get_page tool calls     |
| `agentic_session()`         | Sessions view: all turns of a conversation grouped together for RCA               |
| VoteFeedback                | Signals: 👍/👎 correlated to the exact trace that generated the response          |
| Copy signal (`user-copy`)   | Signals: implicit positive signal — user extracted value                          |
| Abandon signal              | Signals: implicit negative — user left without getting what they needed           |
| Platform synthetics         | Signals: Task Completion, Sentiment Analysis, RAG Faithfulness on every session  |

---

## Phase 1: API Key Setup

══════════════════════════════════════════════════
PHASE 1 · API KEY SETUP
══════════════════════════════════════════════════

> 🔑 Two key types, never mixed. Secret key = server traces. Publishable key = browser feedback widget. The SDK accepts either without erroring — mixing is a silent failure.

**Key types:**
- **Secret key** (`KELET_API_KEY`, prefix `kelet_sk_...`): server-only. Used in `kelet.configure()`. Never expose to frontend.
- **Publishable key** (`VITE_KELET_PUBLISHABLE_KEY`, prefix `kelet_pk_...`): frontend-safe. Used in `KeletProvider`.

**[AskUserQuestion]** "Please paste your Kelet API keys."
- Secret key (kelet_sk_...): I'll paste it in Other
- Publishable key (kelet_pk_...): I'll paste it in Other
- I don't have keys yet — take me to console.kelet.ai/api-keys

**[Developer response]** Provided both keys.

**Project name:** Suggested `docs_ai_prod` based on the app. Instructed: create it in the Kelet console at console.kelet.ai top-nav → project name → "New Project".

**[AskUserQuestion]** "Have you created the Kelet project? What is the exact name you used?"

**[Developer response]** "Created as docs_ai_prod."

**Writing to `.env`:**
```
KELET_API_KEY=kelet_sk_...
KELET_PROJECT=docs_ai_prod
VITE_KELET_PUBLISHABLE_KEY=kelet_pk_...
VITE_KELET_PROJECT=docs_ai_prod
```

**Production secrets:**
- Fly.io (backend): `fly secrets set KELET_API_KEY=kelet_sk_... KELET_PROJECT=docs_ai_prod`
- Vercel (frontend): Dashboard → Settings → Environment Variables → add `VITE_KELET_PUBLISHABLE_KEY` and `VITE_KELET_PROJECT`

**[AskUserQuestion]** "Have you set the production secrets on Fly.io and Vercel?"

**[Developer response]** "Yes, set."

╔══════════════════════════════════╗
║  ✅  Phase 1 complete            ║
╚══════════════════════════════════╝

📍  0a ✅ → 0b ✅ → 0c ✅ → 0d ✅ → 1 ✅ → impl ○

---

## Implementation Plan

**Files to change:**

1. `app/main.py` — add `import kelet` and `kelet.configure()` at module level, after imports
2. `src/routers/chat.py` — add `import kelet` and `import uuid`; wrap `_run_agent_stream` body in `kelet.agentic_session(session_id=session.session_id)`; wrap `chat_stateless` body with a new UUID session
3. `frontend/src/main.tsx` — add `KeletProvider` wrapping app root
4. `frontend/src/App.tsx` — add `AssistantMessage` component with `VoteFeedback`, copy button, and `useKeletSignal`; add abandon signal in `useEffect`
5. `.env` — add `KELET_API_KEY`, `KELET_PROJECT`, `VITE_KELET_PUBLISHABLE_KEY`, `VITE_KELET_PROJECT`

**[ExitPlanMode — developer approved]**

---

## Implementation

### app/main.py

Added `import kelet` and `kelet.configure()` at module level — reads `KELET_API_KEY` and `KELET_PROJECT` from environment automatically. Called once at startup (not per-request).

### src/routers/chat.py

Added `import kelet` and `import uuid`.

In `_run_agent_stream()`: wrapped the entire generator body (including `[DONE]` sentinel and session save) in `async with kelet.agentic_session(session_id=session.session_id)`. Critical: the wrapper covers the entire body including the `[DONE]` yield — wrapping only the `chat_agent.iter` call would drop trailing spans silently.

In `chat_stateless()`: added `stateless_session_id = str(uuid.uuid4())` and wrapped the `chat_agent.iter` call with `async with kelet.agentic_session(session_id=stateless_session_id)`. Without this, GET /chat traces appear as isolated unlinked spans — pydantic-ai auto-instruments spans but doesn't set a session ID.

### frontend/src/main.tsx

Added `KeletProvider` wrapping entire app with `apiKey={import.meta.env.VITE_KELET_PUBLISHABLE_KEY}` and `project={import.meta.env.VITE_KELET_PROJECT}`.

### frontend/src/App.tsx

Extracted `AssistantMessage` component to keep the feedback logic clean. Inside it:

1. `VoteFeedback.Root` with `session_id={sessionId}` — immediately below the message content
2. `VoteFeedback.UpvoteButton asChild` + `VoteFeedback.DownvoteButton asChild` with custom `className={styles.iconBtn}` buttons — matches existing button style without introducing new CSS
3. `VoteFeedback.Popover` with `position: absolute; bottom: calc(100% + 8px)` floating above buttons, parent has `position: relative`
4. `VoteFeedback.Textarea` + `VoteFeedback.SubmitButton` with `className={styles.sendBtn}`
5. Copy button with `useKeletSignal()` sending `user-copy` event

In `App` component:
- Added `useKeletSignal()` for the abandon signal
- Added `useEffect` for `beforeunload` → sends `user-abandon` with `score: 0.0` when session active and messages present

---

## Phase V: Verification

══════════════════════════════════════════════════
PHASE V · VERIFICATION
══════════════════════════════════════════════════

> 🕵️ Proving it works. Kelet silences all SDK errors — a broken integration looks identical to a working one. "Build passed" is not evidence. Only the console confirms it.

**Checklist:**

- [x] `kelet.configure()` called once at startup, not per-request
- [x] `agentic_session()` wraps both `_run_agent_stream` (POST /chat) and `chat_stateless` (GET /chat) — every agentic entry point covered
- [x] `agentic_session()` wraps the ENTIRE generator body including `[DONE]` sentinel — no trailing span loss
- [x] Session ID consistent end-to-end: `create_session()` UUID → `agentic_session(session_id=...)` → `X-Session-ID` header → React state → `VoteFeedback.Root session_id={sessionId}`
- [x] Secret key (`KELET_API_KEY`) is server-only — not in frontend bundle
- [x] Publishable key (`VITE_KELET_PUBLISHABLE_KEY`) used in `KeletProvider` — never the secret key
- [x] `VoteFeedback.UpvoteButton/DownvoteButton` use `asChild` — no nested `<button>` elements
- [x] `VoteFeedback.Popover` has `position: absolute`, parent has `position: relative` — no clipping
- [x] `KELET_PROJECT` env var used — not hardcoded in source
- [x] Production secrets set: `fly secrets set` (backend) + Vercel dashboard (frontend)

**Smoke test:** Trigger an LLM call → open Kelet console at console.kelet.ai → verify sessions appear in Sessions view (allow a few minutes for ingestion). Try a thumbs-down → verify it appears in Signals tab correlated to the session.

**[AskUserQuestion]** "Open the Kelet console. Do you see sessions and signals appearing?"

**[Developer response]** "Yes, sessions are showing up."

╔══════════════════════════════════╗
║  ✅  Phase V complete            ║
╚══════════════════════════════════╝

📍  0a ✅ → 0b ✅ → 0c ✅ → 0d ✅ → 1 ✅ → impl ✅

---

## Summary

Kelet is now fully integrated into docs-ai:

- **Traces**: `kelet.configure()` auto-instruments pydantic-ai — every LLM call, tool use (`search_docs`, `get_page`), latency, and error is captured automatically.
- **Sessions**: `agentic_session()` groups all turns of a conversation together — both POST /chat (multi-turn) and GET /chat (stateless one-shot queries).
- **Signals**: VoteFeedback on every assistant response, copy signal, and abandon signal give Kelet explicit and implicit evidence.
- **Synthetics**: Task Completion, Sentiment Analysis, and RAG Faithfulness run on every session — Kelet does the evaluation work, no code required.
