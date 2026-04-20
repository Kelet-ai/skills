# Eval #4 — fastapi-pydantic-ai-with-react-ui — Transcript

## Developer prompt

> integrate kelet into my app

**App description (provided):** FastAPI backend + pydantic-ai agent. React frontend (Vite).
Plain chat UI — messages in, AI responses out. No feedback buttons at all. Session ID
generated server-side, returned in X-Session-ID response header, stored in React state.
Deployed on Vercel (frontend) + Fly.io (backend).

---

## Welcome

```
🕵️  Welcome to Kelet — your AI detective
```

Concepts taught: trace / signal / synthetic / session / project. Kelet is a reasoning
agent that ingests traces + signals, clusters failures, suggests fixes.

---

## Analysis Pass (silent)

Read:

- `pyproject.toml` — Python 3.13, FastAPI, pydantic-ai, pydantic-settings, redis,
  fakeredis. Package manager = uv (has `uv.lock`). **No existing `kelet` dep.**
- `app/main.py` — FastAPI with `@asynccontextmanager` `lifespan`. Already has `try/finally`
  for Redis + docs_cache teardown → clean hook for `kelet.configure()` + `kelet.shutdown()`.
- `src/routers/chat.py` — `POST /chat` SSE stream; `_run_agent_stream` owns `chat_agent.iter(...)`
  and emits a `[DONE]` sentinel.
- `src/cache/__init__.py` — server-generated UUID per session, persisted in Redis with TTL;
  returned as `X-Session-ID` response header (CORS already `expose_headers=["X-Session-ID"]`).
- `src/settings/__init__.py` — pydantic-settings (loads `.env` into a Settings object, not
  `os.environ`). **Consequence:** must pass `api_key=` + `project=` to `kelet.configure()`
  explicitly — bare call would raise `ValueError`.
- `src/agent/__init__.py` — pydantic-ai `chat_agent` with `search_docs` / `get_page` tools
  (RAG over llms.txt index). Model: Bedrock Claude Sonnet 4.6.
- `frontend/` — scaffolded React + Vite chat UI. `src/App.tsx` already reads `X-Session-ID`
  from the response header and stores it in `useState`. No feedback buttons. No copy button.
- `frontend/.env` — pre-existing `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test` +
  `VITE_KELET_PROJECT=docs-ai-react-eval` (I'll align the project name with whatever we
  confirm at Checkpoint 2 — flagged for overwrite).
- Deployment: `k8s/` (Helm charts + environments), `docker-compose.yml`, `Dockerfile`,
  `Dockerfile.dev`. Developer says Vercel (frontend) + Fly.io (backend) in description.

**Session semantics:** server owns the UUID (Redis) → pydantic-ai auto-instrumentation
won't know it → `agentic_session(session_id=...)` REQUIRED. Without it, VoteFeedback
signals would be captured but silently unlinked from the trace.

**Integration mode:** full (React UI present → VoteFeedback justified).

---

## 📍 MAPPING

```
📍  Mapping 🔄 → Signals ○ → Plan ○ → Implement ○ → Verify ○
```

ASCII diagram:

```
React (Vite) — /frontend
  App.tsx: chat UI → POST /chat
  reads X-Session-ID header → stores in React state (useState)
         │  {message, session_id?}
         ▼
FastAPI — app/main.py (lifespan)
  ├─ Redis (or in-memory fakeredis fallback)
  ├─ docs_cache
  └─ CORSMiddleware (exposes X-Session-ID)
src/routers/chat.py
  POST /chat → session = get_session() ?? create_session()
    └─► SSE stream: chat_agent.iter()    ◄── wrap here
    └─► X-Session-ID response header
         │
         ▼
pydantic-ai Agent (Bedrock Claude)
tools: search_docs, get_page
```

Project map:

```
Use case: Docs Q&A chat (RAG over llms.txt)
Flows → Kelet projects:
  - flow "docs-ai chat" → project "docs-ai-iter8-react"
User-facing: yes (React chat UI)
Stack: FastAPI + pydantic-ai + React (Vite)
Config: .env (pydantic-settings) + frontend/.env (Vite)
Deployment: Fly.io backend + Vercel frontend (k8s/ helm also present)
Mode: full
```

Workflow: user types → React POSTs `/chat` → server resolves or creates Redis session →
pydantic-ai streams SSE → client renders deltas → React stores `X-Session-ID` for
subsequent turns. Success = agent grounds in docs and returns a useful answer.
Failure = hallucinated API, off-topic, empty stream.

### Checkpoint 1 — `AskUserQuestion` #1

> Does this diagram, map, and workflow summary accurately represent your system?
> Anything I missed?

**Developer:** *confirmed mapping.*

```
✅  Mapping → 🔄 Signals → ○ Plan → ○ Implement → ○ Verify
```

---

## 🕵️ SIGNALS (internal reasoning — final proposals below)

Synthetic evaluators (managed, zero code — platform responsibility):

- `Task Completion` (llm) — universal anchor. Did the agent actually answer the docs question?
- `RAG Faithfulness` (llm) — claims grounded in retrieved docs vs fabricated (this IS a RAG agent).
- `Answer Relevancy` (llm) — off-topic / padding detection.
- `Sentiment Analysis` (llm) — user frustration, repeated corrections across multi-turn.

No overlap — one per category (Usefulness, Correctness, Usefulness-lite, User reaction).

Coded signals (≤2 total, frontend-only):

- `VoteFeedback` 👍/👎 — primary explicit signal. Adding from scratch next to each AI bubble.
- `useKeletSignal` copy-to-clipboard — implicit "user found this useful enough to save."
  Low-cost wire; high value on docs/RAG apps.

Deferred: rephrase (always synthetic — `Sentiment Analysis` covers it).
Deferred: abandon / retry — no explicit trigger in a plain chat; not worth coding without one.

---

## 📋 PLAN

```
✅  Mapping → ✅ Signals → 🔄 Plan → ○ Implement → ○ Verify
```

**Server:**

1. Add `kelet` to `pyproject.toml` deps (uv).
2. Add `kelet_api_key` + `kelet_project` to `Settings`.
3. `app/main.py` — in `lifespan`: `kelet.configure(api_key=..., project=...)` gated on
   the API key only (AND-gating on project would turn a blank-project drift into silent
   no-traces); `kelet.shutdown()` in the existing `finally:` block.
4. `src/routers/chat.py` — wrap the **entire** SSE generator body in
   `async with kelet.agentic_session(session_id=session.session_id):` including the
   `[DONE]` sentinel (streaming gotcha from common-mistakes.md).

**Frontend:**

5. Add `@kelet-ai/feedback-ui` to `frontend/package.json`.
6. `src/main.tsx` — wrap `<App/>` in `<KeletProvider apiKey={VITE_KELET_PUBLISHABLE_KEY} project={VITE_KELET_PROJECT}>`.
7. `src/App.tsx` — add `VoteFeedback.Root session_id={sessionId}` next to each AI bubble
   (session_id comes from `X-Session-ID` header already captured in `useState`). Add a
   copy-to-clipboard button using `useKeletSignal` (`trigger_name: "user-copy"`,
   `kind: EVENT`, `source: HUMAN`).
8. Style to match the existing dark palette — small pill buttons, muted, no emoji defaults,
   active state using the existing `--accent` token. On-brand with the chat bubbles; NOT
   a floating widget.

**Env:**

9. `.env` — add `KELET_API_KEY` + `KELET_PROJECT=docs-ai-iter8-react`.
10. `frontend/.env` — has `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test` already. Update
    `VITE_KELET_PROJECT` from the existing `docs-ai-react-eval` to `docs-ai-iter8-react`
    to match server.

What you'll see in the Kelet console:

| After implementing              | Visible in Kelet console                             |
| ------------------------------- | ---------------------------------------------------- |
| `kelet.configure()`             | LLM spans in Traces: model, tokens, latency, errors  |
| `agentic_session()`             | Sessions view: full conversation grouped for RCA     |
| VoteFeedback                    | Signals: 👍/👎 correlated to exact trace             |
| useKeletSignal (user-copy)      | Signals: copy events — implicit usefulness indicator |
| Platform synthetics (4 chosen)  | Signals: automated quality scores                    |

### Checkpoint 2 — `AskUserQuestion` #2 (multiSelect)

> 1. Proposed synthetic evaluators — pick any (multiSelect):
>    Task Completion · RAG Faithfulness · Answer Relevancy · Sentiment Analysis · None
> 2. Plan approval: does the rest of the plan look right?
> 3. Project name confirmation — `docs-ai-iter8-react` OK?
> 4. API key mode:
>    (a) Paste secret key (sk-kelet-...)  — primary auto-create
>    (b) I'll grab one — halt until you paste
>    (c) I can't paste secrets here — deeplink fallback

**Developer answered:**

- Synthetics: **all four** (Task Completion, RAG Faithfulness, Answer Relevancy,
  Sentiment Analysis).
- Plan: **approved**.
- Project name: **`docs-ai-iter8-react`**.
- Key mode: **(a) Paste secret key** → `sk-kelet-eval-test`.
- Publishable key (follow-up): **`pk-kelet-eval-test`**.

---

### Creating evaluators (primary path — key pasted)

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) — Kelet
> generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

Bash:

```
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-iter8-react/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"Docs Q&A chat (pydantic-ai RAG over llms.txt indexed doc pages)","ideas":[...4 ideas...]}'
```

Response:

```
created=4 updated=0 failed=0 deduped=false
200
```

✅ Created 4 evaluators in `docs-ai-iter8-react`: Task Completion, RAG Faithfulness,
Answer Relevancy, Sentiment Analysis. First results in ~3min at
https://console.kelet.ai/docs-ai-iter8-react/signals

```
✅  Mapping → ✅ Signals → ✅ Plan → 🔄 Implement → ○ Verify
```

---

## 🔧 IMPLEMENT

Files changed (server):

- `pyproject.toml` — added `kelet>=0.1`.
- `src/settings/__init__.py` — added `kelet_api_key: str = ""` and `kelet_project: str = ""`.
- `app/main.py` — `import kelet`; `kelet.configure(api_key=settings.kelet_api_key,
  project=settings.kelet_project)` gated on the key at the top of `lifespan`;
  `kelet.shutdown()` in the existing `finally:` block after `redis.aclose()`.
- `src/routers/chat.py` — `import kelet`; wrapped the entire `_run_agent_stream`
  body (setup, streaming loop, session persistence, `[DONE]`) in
  `async with kelet.agentic_session(session_id=session.session_id):`.

Files changed (frontend — new scaffold was added as part of this eval's pre-seed):

- `frontend/package.json` — added `@kelet-ai/feedback-ui`.
- `frontend/src/main.tsx` — `<KeletProvider apiKey={...} project={...}>` wrapping `<App/>`.
- `frontend/src/App.tsx` — new `AiMessage` + `CopyButton` components. `VoteFeedback.Root
  session_id={sessionId}` next to each AI bubble with `asChild` on the up/down buttons to
  avoid nested `<button>`s. Copy button uses `useKeletSignal` with `kind: EVENT, source:
  HUMAN, trigger_name: "user-copy"`. Session ID from `res.headers.get('X-Session-ID')` →
  `useState` → propagated to both `VoteFeedback` and the copy signal.
- `frontend/src/styles.css` — added `.chat-ai`, `.chat-actions`, `.chat-vote`,
  `.chat-action`, `.chat-vote-btn.is-active` using existing palette tokens
  (`--text-muted`, `--panel`, `--accent`, `--border`). Pill buttons, same font stack,
  same radii — fits the dark chat theme.

Env:

- `.env` — appended `KELET_API_KEY=sk-kelet-eval-test` + `KELET_PROJECT=docs-ai-iter8-react`
  (secret key server-only, never in the frontend bundle).
- `frontend/.env` — `VITE_KELET_PROJECT` updated from `docs-ai-react-eval` to
  `docs-ai-iter8-react`. `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test` already present.

```
✅  Mapping → ✅ Signals → ✅ Plan → ✅ Implement → 🔄 Verify
```

---

## 🕵️ VERIFY

- [x] `kelet.configure()` called at startup (not per request) — inside `lifespan`, gated
      on `settings.kelet_api_key` (empty project with a valid key surfaces in console as
      a routing error; AND-gating would hide that).
- [x] `agentic_session(session_id=...)` wraps the entire streaming generator including
      `[DONE]`. Server owns the session ID (Redis) → required even though pydantic-ai
      is auto-instrumented.
- [x] `kelet.shutdown()` in FastAPI `lifespan` `finally:` block — last seconds of spans
      flushed on pod rotation / Fly deploy / SIGKILL.
- [x] Secret key in `.env` (server-only). Publishable key in `frontend/.env` (Vite picks
      up `VITE_KELET_PUBLISHABLE_KEY`).
- [x] `KELET_PROJECT` as env var (not hardcoded in source).
- [x] `KeletProvider` at React root with publishable key.
- [x] `VoteFeedback.Root session_id={sessionId}` next to each AI message (not a floating
      widget, not a separate page).
- [x] `asChild` pattern on Up/Down buttons → no nested `<button>` (avoids invalid HTML
      and HMR corruption).
- [x] Session ID from `X-Session-ID` response header → captured in React `useState` →
      passed to `VoteFeedback.Root session_id` and to `useKeletSignal().sendSignal`.
      End-to-end ID match — no silent-unlink.
- [x] One implicit frontend signal beyond VoteFeedback: copy-to-clipboard via
      `useKeletSignal` with `trigger_name: "user-copy"`.
- [x] Styling matches existing palette tokens — pill buttons, muted text, active state
      with `--accent` border. Not a jarring out-of-place widget.
- [x] CORS already exposes `X-Session-ID` — browser can read the header.

**Smoke test (manual — developer must do):** `uv sync`, `uv run python app/main.py`, in
`frontend/` run `npm install && npm run dev`, open `http://localhost:5173`, send a
message, click 👍 / 👎 / Copy. Open https://console.kelet.ai/docs-ai-iter8-react —
sessions should appear within a minute and signals within a few.

```
✅  Mapping → ✅ Signals → ✅ Plan → ✅ Implement → ✅ Verify
```

Done.
