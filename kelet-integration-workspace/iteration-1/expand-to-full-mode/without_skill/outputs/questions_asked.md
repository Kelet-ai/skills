# Questions Asked

None were asked of the developer. The task was treated as autonomous exploration and implementation.

---

## Questions that SHOULD have been asked (but weren't, due to autonomous mode)

### 1. What is the exact `kelet.signal()` API signature?
**Why it matters:** I assumed `source`, `label`, `value`, `session_id`, `metadata` parameters exist. The real SDK might use different parameter names (e.g. `event_type` instead of `label`, `score` instead of `value`). If wrong, all signal calls will fail or emit malformed data.

**Where the assumption was made:**
- All `kelet.signal()` calls in `src/routers/chat.py` and `src/agent/__init__.py`

### 2. Is `source="FEEDBACK"` a valid source type, or should it be something else?
**Why it matters:** The `source` field may be an enum with restricted values. Using an unknown value might cause the call to fail silently or raise an exception at runtime.

### 3. Is there a `kelet.signal()` function at all, or is explicit signaling done differently?
**Why it matters:** For the basic integration, only `kelet.configure()` and `kelet.agentic_session()` were used. The SDK may not expose a standalone `kelet.signal()` function — signals might be emitted differently (e.g. via a different API, or only through pydantic-ai integration hooks).

### 4. Can tool-level signals be linked to the current session?
**Why it matters:** pydantic-ai's `RunContext[DocsDeps]` doesn't expose the Kelet session ID. Tool signals can't be linked to the session without passing `session_id` through `DocsDeps`. Should the developer add `session_id: str | None` to `DocsDeps` and pass it through?

### 5. Is plain-HTML feedback the right approach, or should a different feedback mechanism be used?
**Why it matters:** Without `@kelet-ai/feedback-ui`, the developer needs to implement their own thumbs widget in plain HTML/JS. Alternatively, Kelet may have a different recommended approach for non-React apps (e.g. a script tag widget, or a server-side-only approach).
