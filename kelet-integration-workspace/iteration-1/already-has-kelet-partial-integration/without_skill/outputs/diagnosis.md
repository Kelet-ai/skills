# Diagnosis: Sessions Not Appearing in Kelet Console

## Problem Statement

Kelet is installed (`kelet>=1.3.0` in pyproject.toml) and `kelet.configure()` is called at startup in `app/main.py`. The app uses pydantic-ai and Kelet is receiving traces — but each request appears as a separate, unlinked trace in the console rather than being grouped into sessions.

## Root Cause

`kelet.configure()` sets up the OpenTelemetry tracing pipeline and instruments pydantic-ai so that LLM calls generate spans. However, it has no way to know which conversation a given LLM call belongs to — that information must be provided explicitly by the application using `kelet.agentic_session()`.

The missing piece is `kelet.agentic_session(session_id=...)`.

Without it:
- Each call to `chat_agent.iter(...)` generates its own isolated root span
- There is no `gen_ai.conversation.id` attribute on the spans
- The Kelet console cannot group related turns into a session view — every message appears as a separate unlinked trace

With `agentic_session()`:
- A context is established that stamps `gen_ai.conversation.id` (the `session_id`) on every span inside it via OTel baggage and ContextVar
- All LLM calls made within the context (including tool calls) share the same session ID
- The console can group and display them as a multi-turn conversation

## Evidence

From `kelet/__init__.py` (installed package docstring):

```python
# Standalone usage shows agentic_session() as a required step:
with kelet.agentic_session(session_id="session-123"):
    result = await agent.run(...)
```

From `kelet/_context.py`:
- `agentic_session()` sets `_session_id_var` ContextVar and injects `gen_ai.conversation.id` as OTel baggage
- Without this, spans have no conversation linkage

From `src/routers/chat.py` (before fix):
- `chat_agent.iter(message, deps=deps, message_history=message_history)` called with no `agentic_session` wrapper
- The app already has `session.session_id` available (a UUID tracked in Redis), but it was never passed to Kelet

## How the Diagnosis Was Made

1. Confirmed `kelet` package is present in `pyproject.toml` and `kelet.configure()` is called in `app/main.py` — so the instrumentation pipeline is active.
2. Read the kelet package `__init__.py` docstring — it shows `agentic_session()` as a required wrapping step in all usage examples.
3. Inspected `src/routers/chat.py`: the `_run_agent_stream` function calls `chat_agent.iter(...)` directly with no `agentic_session` context.
4. Confirmed the app already maintains a `session.session_id` UUID per conversation in Redis — this is the natural value to pass to `agentic_session()`.
5. Read `_context.py` to confirm the mechanics: without `agentic_session`, spans have no `gen_ai.conversation.id` and appear as disconnected root spans.

## The Fix

Wrap every agent invocation with `async with kelet.agentic_session(session_id=...)`, passing the application's existing session ID:

```python
# In _run_agent_stream (src/routers/chat.py):
async with kelet.agentic_session(session_id=session.session_id):
    async with chat_agent.iter(message, deps=deps, message_history=message_history) as run:
        async for node in run:
            ...
```

The `session.session_id` is already available in `_run_agent_stream` as it is passed in from the `chat` endpoint handler where the session is resolved/created.

## Files Changed

- `app/main.py` (partial integration setup): Added `import kelet` and `kelet.configure()` call
- `src/routers/chat.py` (the fix): Added `import kelet`; wrapped `_run_agent_stream` body with `async with kelet.agentic_session(session_id=session.session_id)`
