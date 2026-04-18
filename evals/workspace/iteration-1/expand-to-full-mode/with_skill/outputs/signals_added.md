# Signals Added — Expand to Full Mode

## Summary

4 new coded signals added across 2 files. No VoteFeedback (no React, plain HTML frontend). No source=SYNTHETIC code (platform handles all evaluators).

---

## Coded Signals

### 1. `agent-stream-error`
**File:** `src/routers/chat.py` — `_run_agent_stream()` except block
**Kind:** EVENT  **Source:** LABEL  **Score:** 0.0

Fires when the top-level agent execution throws an uncaught exception (model timeout, context window exceeded, Bedrock API error, pydantic-ai internal error). Previously this path only logged and streamed an error SSE — Kelet had no visibility. Now every hard failure is tagged and correlated to the session.

**What it catches:**
- Bedrock API errors (throttling, model unavailability)
- pydantic-ai streaming failures
- Unexpected exceptions inside the agent loop

---

### 2. `session-expired-return`
**File:** `src/routers/chat.py` — `chat()` POST handler, session resolution block
**Kind:** EVENT  **Source:** HUMAN  **Score:** 0.0

Fires when a client submits a `session_id` that is no longer in Redis. This is the clearest server-detectable abandonment signal: the user had an active session (browser has the ID), walked away for more than 30 minutes, and returned. Kelet clusters these by session ID so the previous session's traces can be analyzed for what drove the user away.

**What it catches:**
- Implicit session abandonment (user left mid-conversation)
- TTL-expired sessions that suggest unsatisfied conversations
- Patterns of abandonment correlated to specific question types or failure modes

---

### 3. `tool-search-error`
**File:** `src/agent/__init__.py` — `search_docs()` tool
**Kind:** EVENT  **Source:** LABEL

Fires if the BM25 search index raises an exception (index not yet loaded, corrupted cache, unexpected query format). Previously the exception would bubble up and surface as a generic agent error. Now the specific tool failure is tagged with the query that caused it.

**What it catches:**
- DocsCache search failures
- Index not-yet-loaded errors
- Any exception inside the BM25 retrieval path

---

### 4. `tool-page-not-found` + `tool-page-error`
**File:** `src/agent/__init__.py` — `get_page()` tool
**Kind:** EVENT  **Source:** LABEL

Two signals covering distinct failure modes in the page retrieval tool:
- `tool-page-not-found`: Agent requested a slug that doesn't exist in the index. Common when the model hallucinates a slug or uses stale index data. Score not set (informational).
- `tool-page-error`: Unexpected exception during page fetch (cache read failure, deserialization error). Score not set (exception path).

**What they catch:**
- Model hallucinating document slugs
- Stale index references (slug renamed after last crawl)
- Cache read failures in DocsCache.get_page()

---

## Synthetic Evaluators (Platform — Zero Code)

Activated via deeplink at `https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=...`

| Evaluator | Type | Failure Category | What it measures |
|-----------|------|-----------------|-----------------|
| Task Completion | llm | Usefulness | Did the agent fully answer the developer question, including sub-questions? |
| Sentiment Analysis | llm | User Reaction | Did the user show frustration, repeated corrections, escalating dissatisfaction? |
| Conversation Completeness | llm | Comprehension | Were any user intentions left unaddressed or deflected without resolution? |
| Role Adherence | llm | Behavior | Did the agent stay within Kelet documentation scope, refusing off-topic requests? |

Not selected: RAG Faithfulness (requires retrieval context passed to evaluator — not wired), Hallucination Detection (overlaps with Role Adherence for this use case), Loop Detection (no multi-step tool loops in this agent).

---

## Skipped (Already Present in Baseline)

- `kelet.configure()` — already in app/main.py
- `kelet.agentic_session()` — already wrapping agent call in chat.py
- `KELET_API_KEY` / `KELET_PROJECT` — already in .env and k8s secrets

## Not Added (No Hook Exists)

- VoteFeedback / thumbs up/down — no React, plain HTML frontend. The skill's `@kelet-ai/feedback-ui` is React-only. A plain JS fetch to a `/chat/feedback` endpoint would be the path, but the developer did not request frontend work and the existing HTML frontend has no existing feedback UI hook.
