# Expansion Transcript — Without Skill

## Task
Developer already has `kelet.configure()` in `app/main.py` and `kelet.agentic_session()` in `src/routers/chat.py`. Goal: add more signals and better failure coverage.

## Exploration

### Repo Structure
- `app/main.py` — FastAPI app setup, `kelet.configure()` at module level
- `src/routers/chat.py` — POST /chat (SSE streaming), GET /chat (stateless), `kelet.agentic_session()` wrapping the agent
- `src/agent/__init__.py` — pydantic-ai Agent with two tools: `search_docs` and `get_page`
- `src/cache/__init__.py` — Redis session CRUD
- `src/rate_limiter/__init__.py` — fixed-window IP-based rate limiter
- `src/settings/__init__.py` — pydantic-settings config
- `src/docs_loader/__init__.py` — BM25 docs index with BFS fetcher

### Starting state (baseline)
- `kelet.configure()` present in `app/main.py`
- `kelet.agentic_session(session_id=session.session_id)` wraps agent call in `_run_agent_stream`
- No other signals anywhere

## Decisions

### 1. Add `user_id` to `agentic_session`
The `ChatRequest` model was missing `phone_number` (the only persistent user ID), so Kelet could not link turns across sessions to the same user. Added `phone_number: str | None` to `ChatRequest` and passed it as `user_id` to `kelet.agentic_session()`.

**Rationale:** Without `user_id`, every session appears as an anonymous user. Linking by phone number enables per-user quality trends.

### 2. Instrument rate-limit events
When `check_rate_limit` returns False (user is throttled), nothing was signaled to Kelet. Added `kelet.signal(source="INTERNAL", label="rate_limited", value=1)` before raising HTTP 429, in both POST and GET `/chat`.

**Rationale:** Rate-limit hits are a failure signal — they indicate frustrated users who are trying to use the product but being blocked. Surfacing them in Kelet makes the rate-limit setting tunable with data.

### 3. Instrument agent exceptions
The `except Exception` block in `_run_agent_stream` was silently logging and returning an error SSE. Added `kelet.signal(source="INTERNAL", label="agent_error", session_id=session.session_id, value=1)`.

**Rationale:** Agent errors are the most important failure mode. Without a signal, they only appear in logs. Kelet can correlate error rate with user query patterns.

### 4. Add explicit user feedback endpoint
Added `POST /chat/feedback` with `FeedbackRequest(session_id, score: float 0–1, comment: str | None)`. Validated that the session exists before recording. Calls `kelet.signal(source="FEEDBACK", label="user_feedback", ...)`.

**Rationale:** Explicit feedback (thumbs up/down + optional comment) is the highest-quality signal available. Plain HTML frontend means no React `@kelet-ai/feedback-ui` component — a simple REST endpoint lets the developer wire up a native thumbs widget in the existing HTML.

**Uncertainty:** `kelet.signal()` API shape was guessed from general Kelet SDK knowledge — specifically `source`, `label`, `value`, `session_id`, `metadata` parameters. Not verified against actual SDK docs.

### 5. Instrument `search_docs` no-results and `get_page` not-found
- `search_docs`: emits `search_docs_no_results` (value=1) when BM25 returns no relevant results.
- `get_page`: emits `get_page_not_found` (value=1, metadata={"slug": ...}) when a requested slug doesn't exist.

**Rationale:** These tool failures indicate gaps in the docs corpus. If the agent frequently hits no-results, it means users are asking about topics not covered. If `get_page` fails, it means the agent is hallucinating slugs. Both are actionable quality signals.

**Uncertainty:** `kelet.signal()` is called without a `session_id` in tool context because the tool function only receives `RunContext[DocsDeps]` which doesn't expose the session ID. This means these signals won't be linked to the correct session in Kelet — a limitation of instrumentation at the tool level rather than the session level.

## Files Modified
1. `src/routers/chat.py` — user_id, rate-limit signals, agent error signal, feedback endpoint
2. `src/agent/__init__.py` — tool-level no-results and not-found signals
