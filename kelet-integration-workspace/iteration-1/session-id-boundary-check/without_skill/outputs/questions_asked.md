# Questions Asked

**No questions were asked.**

The integration was performed entirely based on:
1. Reading the existing codebase
2. Reading the installed `kelet` package source
3. Inferring intent from the developer's app description

---

## Decisions Made Without Asking

| Decision | What was assumed / done |
|----------|------------------------|
| Session ID | Used internal UUID `session_id` from Redis ChatSession |
| User ID | NOT handled — phone number has no path into the code, problem was abandoned |
| `kelet.configure()` guard | Unconditional call — crashes if KELET_API_KEY is missing |
| Stateless endpoint | Left unwrapped — no `kelet.agentic_session` |
| Feedback signals | Not added |

---

## Questions That Should Have Been Asked

### 1. "How does the phone number reach the server at request time?"

This is the critical question. The developer said phone number is the only user identifier,
but it's absent from all request models and session data. Possible answers:
- Client sends it explicitly in the POST body
- Extracted from a JWT/auth header
- Looked up from a user database by some other identifier

Without knowing this, `user_id` was simply omitted from `kelet.agentic_session()`.

### 2. "When you say 'users can start fresh conversations' — should Kelet see those as separate sessions or one continuous session per user?"

This determines whether `session_id` should be:
- The UUID (a new session per conversation) — traces each conversation separately
- The phone number (treats all conversations from one user as one session) — simpler but loses conversation boundaries

### 3. "Do you want to capture user feedback (thumbs up/down)?"

`kelet.signal()` can record explicit user feedback. Was not asked about, so not implemented.
