# Signals Added

## 1. `user_id` passed to `agentic_session`
- **Where:** `src/routers/chat.py` — `_run_agent_stream` + `ChatRequest`
- **What:** Added `phone_number: str | None` field to `ChatRequest`; passed as `user_id=body.phone_number` to `kelet.agentic_session()`
- **Source type:** Core session metadata (not a discrete signal call)
- **Rationale:** Links turns to a persistent user identity so Kelet can show per-user quality trends

## 2. Rate-limit signal
- **Where:** `src/routers/chat.py` — both `chat_stateless` (GET) and `chat` (POST)
- **Signal call:** `kelet.signal(source="INTERNAL", label="rate_limited", value=1)`
- **When emitted:** When `check_rate_limit()` returns False (user exceeds 20 req/hour)
- **Rationale:** Rate-limit hits are invisible without a signal. Tracking them allows the developer to tune the rate limit based on real usage patterns.

## 3. Agent error signal
- **Where:** `src/routers/chat.py` — `_run_agent_stream` except block
- **Signal call:** `kelet.signal(source="INTERNAL", label="agent_error", session_id=session.session_id, value=1)`
- **When emitted:** When the agent raises any exception during streaming
- **Rationale:** Most critical failure mode. Links the error to the session so Kelet can show which types of queries trigger failures.

## 4. Explicit user feedback signal
- **Where:** `src/routers/chat.py` — new `POST /chat/feedback` endpoint
- **Signal call:** `kelet.signal(source="FEEDBACK", label="user_feedback", session_id=body.session_id, value=body.score, metadata={"comment": ...})`
- **Input:** `score: float` (0.0 = bad, 1.0 = good), `comment: str | None`
- **Rationale:** Highest quality signal type. No React component possible (plain HTML), so a REST endpoint allows a simple native thumbs widget in the existing HTML frontend.

## 5. Search no-results signal
- **Where:** `src/agent/__init__.py` — `search_docs` tool
- **Signal call:** `kelet.signal(source="INTERNAL", label="search_docs_no_results", value=0|1)`
- **When emitted:** Every `search_docs` call; value=1 when no relevant results found, value=0 when results returned
- **Rationale:** Tracks coverage gaps in the docs corpus. High no-results rate = docs don't cover what users ask.
- **Limitation:** No `session_id` available in tool context — signal is unlinked from session

## 6. Get-page not-found signal
- **Where:** `src/agent/__init__.py` — `get_page` tool
- **Signal call:** `kelet.signal(source="INTERNAL", label="get_page_not_found", value=1, metadata={"slug": slug})`
- **When emitted:** When the requested slug does not exist in the docs cache
- **Rationale:** Tracks hallucinated or stale slugs. The `slug` metadata enables tracking which specific pages are missing.
- **Limitation:** No `session_id` available in tool context — signal is unlinked from session
