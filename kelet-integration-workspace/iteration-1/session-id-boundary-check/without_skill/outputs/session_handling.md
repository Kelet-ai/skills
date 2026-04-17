# Session ID Handling — Without Skill

## The Problem

The developer described:
> "User identity = phone number stored in DB. No per-conversation UUID — phone number is the only identifier."

But the codebase has a UUID-based session system in Redis (`ChatSession` with a UUID `session_id`).
The phone number appears nowhere in the code.

## How It Was Handled (Final State)

### Session ID: UUID used as-is

`kelet.agentic_session(session_id=session.session_id)` — the internal Redis UUID is passed
directly as the Kelet session ID.

### User ID: NOT handled

`user_id` was not passed to `kelet.agentic_session()`. The phone number problem was recognized
but ultimately not resolved in the final code. The integration silently ignores user identity.

```python
# What was implemented (NO user_id):
async with kelet.agentic_session(session_id=session.session_id):
    async with chat_agent.iter(...) as run:
        ...
```

## Why user_id Was Dropped

1. Phone number is not available in the request body (`ChatRequest` has no `phone_number` field)
2. Phone number is not stored in the Redis `ChatSession` object
3. There is no auth middleware to extract phone number from a token/header
4. Adding a `phone_number` field to `ChatRequest` was attempted but ultimately reverted

The integration went with the path of least resistance: use what's available (UUID session_id)
and leave the user identity question unresolved.

## Semantic Mismatch Summary

| Concept | Developer's intent | What Kelet got |
|---------|-------------------|----------------|
| User identity | Phone number | Nothing (no user_id) |
| Session ID | Phone number (only identifier) | UUID per conversation |
| Fresh conversation | New start, same user | New UUID session, no user link |

## Key Failure Mode

Without `user_id`, Kelet cannot:
- Group all conversations from one phone number under a single user
- Show per-user quality trends
- Detect if a specific user is getting bad responses

Each conversation appears as an anonymous session with no user attribution.

## What Should Have Been Done

Option A — Use phone number as user_id (add it to ChatRequest):
```python
class ChatRequest(BaseModel):
    ...
    phone_number: str | None = None  # user identity

async with kelet.agentic_session(
    session_id=session.session_id,
    user_id=body.phone_number,
):
    ...
```

Option B — Ask the developer how phone number reaches the server (JWT? explicit field?
looked up from DB by session?), then wire accordingly.

Option C (if phone = session in their mental model) — Use phone number AS the session_id:
```python
async with kelet.agentic_session(
    session_id=body.phone_number,  # treats all messages from user as one session
):
    ...
```
