# Integration Transcript: Without Kelet Skill

## Task
Integrate Kelet into a FastAPI + pydantic-ai backend with a React/Vite frontend.

## App Description
- FastAPI backend with pydantic-ai agent
- React frontend (Vite)
- Plain chat UI — messages in, AI responses out (no feedback buttons in initial state)
- Session ID generated server-side, returned in X-Session-ID response header, stored in React state
- Deployed on Vercel (frontend) + Fly.io (backend)

---

## Steps Taken (simulated "without skill" behavior)

### Step 1: Explore the repo

Explored the repository structure:
- `app/main.py` — FastAPI app entry point, lifespan, middleware
- `src/agent/__init__.py` — pydantic-ai Agent definition with two tools (search_docs, get_page)
- `src/routers/chat.py` — chat endpoints (GET /chat stateless, POST /chat SSE streaming)
- `src/settings/__init__.py` — pydantic-settings config
- `pyproject.toml` — dependencies
- `frontend/src/App.tsx` — React chat UI (initial: no feedback buttons)

Noted that:
- `kelet>=1.3.0` was already listed in pyproject.toml (good baseline)
- The README mentions Kelet but doesn't explain SDK integration — points to a Claude Code skill
- Session ID flows correctly: server creates it, returns in X-Session-ID header, client stores and sends back

### Step 2: Add kelet.configure() to app startup

**Decision**: Call `kelet.configure()` at module level in `app/main.py` so it initializes before any request arrives. This reads `KELET_API_KEY` and `KELET_PROJECT` from environment.

**Uncertainty**: Not sure if `kelet.configure()` takes any arguments or if env-based config is sufficient.

### Step 3: Wrap agent execution with session tracing

**Decision**: Used `async with kelet.session(session_id=session.session_id)` to wrap the pydantic-ai `chat_agent.iter()` call.

**Key uncertainty / likely mistake**: Without the skill, Claude guesses the context manager is called `kelet.session()`. The correct API is `kelet.agentic_session()`. This is a silent failure mode — no import error, but the session may not be properly tracked as an "agentic" session in Kelet's dashboard.

### Step 4: Add error signal on agent failure

Added `kelet.signal(session_id=..., label="agent_error", value=1)` in the except block.

**Likely mistakes**:
- Called `kelet.signal()` synchronously — may need to be awaited (`await kelet.signal(...)`)
- Guessed the signal API signature: `kelet.signal(session_id, label, value)` — actual API uses positional `source` and `label` args plus keyword `session_id`
- No `source` parameter specified — the correct API requires a `source` (e.g. `"INTERNAL"`)

### Step 5: Add feedback endpoint (backend)

Added `POST /chat/feedback` endpoint that:
1. Validates session exists
2. Converts "up"/"down" vote to 1.0/0.0 score
3. Calls `kelet.signal(session_id=..., label="user_feedback", value=score)`

**Likely mistakes**:
- Used `kelet.signal()` synchronously (not awaited)
- Did not use `source="FEEDBACK"` in the signal call — the correct `source` for user feedback is `"FEEDBACK"`, not missing
- The score/value mapping to `source` semantics is unclear without the skill

### Step 6: React frontend — add feedback buttons

**Decision**: Added thumbs up/down buttons directly in JSX (inline HTML, no component library).

**What was NOT done**:
- Did not install or use `@kelet-ai/feedback-ui` React component (didn't know it existed)
- Did not know about the publishable key vs secret key distinction for frontend vs backend
- No Kelet frontend SDK initialization

**What was done correctly**:
- Session ID is read from `X-Session-ID` response header and stored in React state
- Session ID is sent back on subsequent requests
- Feedback endpoint is called with session_id when user clicks thumbs up/down
- Feedback endpoint URL used: `/chat/feedback` (correct, matches backend)

### Step 7: Vite proxy config

Updated `vite.config.ts` to proxy `/chat` to the backend (covers both `/chat` and `/chat/feedback` since it's prefix-matched).

---

## Summary of Decisions

| Decision | What was done (no skill) | What the skill would do |
|---|---|---|
| Session tracing API | `kelet.session()` | `kelet.agentic_session()` |
| Signal source arg | Missing | `"INTERNAL"` or `"FEEDBACK"` |
| Signal await | Sync `kelet.signal()` | `await kelet.signal()` |
| Frontend SDK | None | `@kelet-ai/feedback-ui` with publishable key |
| API key type | No frontend key consideration | Publishable key for frontend, secret for backend |
| user_id threading | Not done | Phone number passed as user_id to link sessions |
| Synthetic signals | Not considered | Would set up via deeplink after Phase 0c |
| Tool error signals | Not added to tools | Signal on tool failures (search_docs, get_page) |

---

## Bugs introduced (without skill)

1. **Wrong context manager name**: `kelet.session()` instead of `kelet.agentic_session()` — will likely raise `AttributeError` at runtime or silently use wrong tracing mode
2. **Missing `source` positional arg**: `kelet.signal()` called without required `source` parameter — will raise `TypeError`
3. **Synchronous signal call**: `kelet.signal(...)` not awaited in async generator — may cause unawaited coroutine warning or silent data loss
4. **No user identity threading**: `phone_number` not passed as `user_id` — users can't be linked across sessions in Kelet
5. **No publishable key for frontend**: Frontend has no Kelet SDK integration — no client-side event tracking
6. **No tool-level signals**: `search_docs` and `get_page` tools have no error signals
