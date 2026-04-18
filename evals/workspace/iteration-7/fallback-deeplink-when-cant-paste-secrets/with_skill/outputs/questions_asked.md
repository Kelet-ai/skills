# Questions Asked

Total `AskUserQuestion` calls: **2** (within the budget of "ideally 2, max 3").

---

## Question 1 — Checkpoint 1: Mapping Confirmation

**Header:** `🔍 ANALYSIS · PROJECT + WORKFLOW MAPPING`

**Prompt:** "Does this diagram, project map, and workflow summary accurately represent your system? Anything I missed?"

**Options presented:**

1. Looks right — proceed.
2. Correction needed — I'll describe it.

**Context shown before the question:**

- ASCII architecture diagram (Browser → FastAPI `/chat` → pydantic-ai `chat_agent` → Bedrock Claude; Redis holds `ChatSession(session_id, history)`; `session_id` minted server-side via `uuid4` and surfaced via `X-Session-ID` response header).
- Project map:
  - Use case: documentation Q&A over Kelet's `llms.txt` via BM25 retrieval + pydantic-ai.
  - Flows → projects: single flow `docs-chat` → one project.
  - User-facing: yes (browser, plain HTML — no React).
  - Stack: FastAPI + pydantic-ai + Redis (or FakeRedis fallback).
  - Config: `.env` + Fly.io secrets.
  - Deployment: Fly.io (plain-HTML frontend served from the same app).
  - Mode: **lightweight**.
- Session semantics note: `session_id` is minted by the server on first POST, stored in Redis, and returned in `X-Session-ID`. pydantic-ai does not know this ID, so `agentic_session(session_id=...)` is required.

**Simulated answer:** Option 1 — mapping confirmed.

---

## Question 2 — Checkpoint 2: Plan + Inputs

**Header:** `📋 PLAN · SIGNAL STRATEGY + INPUTS`

**Compound `AskUserQuestion` (`multiSelect: true`) with four sub-prompts:**

### 2a. Proposed synthetic evaluators (multiSelect)

Options — developer picks which go into the project:

- `Task Completion` (llm) — did the agent answer the user's docs question?
- `RAG Faithfulness` (llm) — claims grounded in retrieved docs pages.
- `Answer Relevancy` (llm) — on-topic, no padding or deflection.
- `Hallucination Detection` (llm) — fabricated APIs or invented citations.
- `Session Health Stats` (code) — turn counts, token usage, tool-call frequency.
- None.

**Simulated answer:** Selected **all 5** (no "None").

### 2b. Plan approval

"Does the rest of the plan look right?"
Plan summary:
- `kelet.configure()` at FastAPI startup (reads env eagerly).
- `kelet.agentic_session(session_id=session.session_id)` wrapping the pydantic-ai run in POST `/chat`.
- `kelet.agentic_session(session_id=uuid4())` wrapping the stateless GET `/chat`.
- `.env` / `.env.example` updated with `KELET_PROJECT=docs-ai-fallback`. `KELET_API_KEY` left blank locally — set via `fly secrets set` in production.
- No VoteFeedback (no React frontend — plain HTML).
- No coded signals (lightweight mode; nothing meaningful to wire in plain HTML without new UI).

**Simulated answer:** Approved.

### 2c. Project name

Default proposal: `docs-ai-fallback`.
Reminder: create the project first at console.kelet.ai → top-nav → New Project. Wrong name = silent routing failure.

**Simulated answer:** `docs-ai-fallback`.

### 2d. API key mode (because synthetic evaluators were selected)

Options:

- Paste secret key (`sk-kelet-...`) — primary auto-create via API.
- I'll grab one — halt while you fetch a key at console.kelet.ai/api-keys.
- **I can't paste secrets here** — deeplink fallback (no project verification).

**Simulated answer:** "I can't paste secrets here."

**Follow-up from skill:**
> ⚠️ Without a key I cannot verify the project `docs-ai-fallback` exists. Please make sure the name exactly matches what you created at console.kelet.ai. A wrong name is a silent 404.

Skill then generated a base64url-encoded deeplink to `https://console.kelet.ai/docs-ai-fallback/synthetics/setup?deeplink=<payload>` and presented it as a bold clickable markdown link.

---

## Not asked

- Publishable key — not needed; no React frontend, no VoteFeedback in plan.
- Deployment question — inferred from Fly.io context (`fly secrets` path documented in `.env.example`).
