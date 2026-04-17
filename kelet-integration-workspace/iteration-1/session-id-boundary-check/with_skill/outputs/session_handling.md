# Session ID Mismatch Handling

## The Mismatch

**Developer stated:** "User identity = phone number stored in DB. No per-conversation UUID — phone number is the only identifier."

**Code reality (found during silent analysis):**
- `src/cache/__init__.py`: `create_session()` generates `str(uuid.uuid4())` as `session_id`
- Sessions stored in Redis under key `docs-ai:session:<uuid>` with TTL 1800s
- The UUID is returned to clients via `X-Session-ID` response header
- `ChatRequest` model has `session_id: str | None = None` — client passes back the UUID on subsequent turns
- No phone number field anywhere in the server codebase

**Conclusion:** The app ALREADY uses UUID-per-conversation correctly. The developer's mental model was phone-centric (thinking of user identity), but the actual session management code generates fresh UUIDs.

## Detection Path

The skill's session analysis (from `references/implementation.md`) triggered on this check:

```
Is the candidate ID a stable user identifier (phone, email, user_id, device_id)?
└─► Yes ──► ⚠️ It outlives sessions — use as user_id=, generate kelet_session_id UUID per conversation
```

Even though the code was already correct, the developer description ("phone is the only identifier") required surfacing the mismatch at Checkpoint 1 to:
1. Confirm the UUID is actually used as session_id (yes, confirmed by code)
2. Propose passing phone as `user_id` to Kelet for cross-session user analytics

## How It Was Handled

**At Checkpoint 1** (within the mapping question, no separate question slot burned):

The skill noted in the question: "Your app already generates a UUID per conversation — I'd add an optional `phone_number` field to `ChatRequest` so clients can pass it through to Kelet as `user_id` (for cross-session user correlation)."

The developer confirmed this matched their intent.

## Implementation Decision

Rather than generating a new UUID (the app already does this), the fix was:
1. Add `phone_number: str | None = None` to `ChatRequest` — clients can optionally send their phone
2. Pass `user_id=body.phone_number` to `kelet.agentic_session()` — Kelet links sessions to the same user
3. The existing UUID (`session.session_id`) maps to Kelet's `session_id` — correct boundary, no change needed

## agentic_session() Requirement

pydantic-ai is in Kelet's auto-instrumented list, but `agentic_session()` IS still required here because:
- **The app owns the session ID** (stored in Redis, UUID generated server-side)
- The framework doesn't know this ID — without `agentic_session()`, VoteFeedback linkage breaks and sessions appear as unlinked traces

Per the skill's rule: "App owns the session ID (Redis, DB, server-generated): framework doesn't know it → VoteFeedback linkage breaks"

## Code Change

**`src/routers/chat.py`** — `_run_agent_stream`:
```python
async with kelet.agentic_session(
    session_id=session.session_id,  # UUID per conversation (already correct)
    user_id=user_id,                # phone number passed from client (for user analytics)
):
    async with chat_agent.iter(...) as run:
        ...
```

**`src/routers/chat.py`** — `ChatRequest`:
```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None
    current_page_slug: str | None = None
    # Phone number is the only persistent user identifier in this app.
    # Pass it per-request so Kelet can link turns across sessions to the same user.
    phone_number: str | None = None
```

## Correctness Assessment

- The session boundary is correct: UUID changes on new conversation (when `session_id` not sent or expired)
- Phone as `user_id` correctly models "one user, many sessions over time"
- `agentic_session()` wraps the entire generator body including `[DONE]` sentinel — traces will be complete
- The stateless `GET /chat` endpoint also gets a fresh UUID session to capture those traces
