# Transcript — Eval #4: FastAPI + pydantic-ai + new React UI (with_skill)

## Developer

> integrate kelet into my app
>
> (FastAPI backend + pydantic-ai agent. React frontend (Vite) — plain chat UI, messages in, AI responses out, no feedback buttons. Session ID server-side, returned in `X-Session-ID`, held in React state. Deployed: Vercel + Fly.io.)

## Kelet skill — Onboarding (banner + concepts)

`🔍  KELET INTEGRATION · ONBOARDING`

Quick vocabulary before I touch anything:

- **Trace** — auto-captured record of one LLM/tool call (model, inputs, outputs, tokens, latency, error). `kelet.configure()` does this; your pydantic-ai calls require zero code changes.
- **Session** — a group of traces tied to one unit of work (one conversation). How Kelet correlates what happened across multiple LLM turns.
- **Signal** — a tip you drop at a meaningful moment. Thumbs-down = "start looking here". Not a verdict, a pointer.
- **Synthetic** — an automated signal Kelet runs on every session from trace data alone. No code.
- **Project** — one logical flow. Different triggers = different projects. Prod vs staging = different projects.

Plan: silent analysis → at most 2 questions → implementation.

## Analysis Pass (silent)

Read: `pyproject.toml`, `app/main.py`, `src/routers/chat.py`, `src/agent/__init__.py`, `src/cache/__init__.py`, `src/settings/__init__.py`, `.env.example`, `k8s/…`, `docker-compose.yml`.

Findings:

- **Deps.** `kelet>=1.3.0` already pinned. `pydantic-ai>=1.0.15` (auto-instrumented — no `agentic_session()` needed). Package manager: `uv` (`uv.lock` present).
- **Entrypoint.** `app/main.py` — module-level, before `FastAPI()` instance is created. Single place, not per-request.
- **LLM call sites.** `chat_agent.iter(...)` in `src/routers/chat.py` for streaming (POST) and stateless (GET). One flow.
- **Session tracking.** `uuid.uuid4()` generated in `create_session` (`src/cache/__init__.py`), stored under `docs-ai:session:<id>` in Redis (fakeredis fallback), returned as `X-Session-ID` header. New conversation = new UUID, regenerated on expiry / fresh POST without `session_id`. ✅ Correct session mapping — no stable-user-identity mismatch.
- **User identity.** None present. No PII, no `user_id=` risk.
- **Existing feedback UI.** None — no React frontend in this branch at all. No thumbs, edits, copy.
- **Deployment infra.** `k8s/charts/docs-ai/` (helm), `.github/workflows/build-and-push.yml`, `docker-compose.yml`. User mentioned Vercel (frontend) + Fly.io (backend). No `fly.toml` / `vercel.json` yet — secrets will go into those platforms' secret stores at deploy time.

### ASCII architecture

```
         ┌────────────────┐          POST /chat  {message, session_id?}
         │ React (Vite)   │ ───────────────────────────────────────┐
         │  App.tsx       │                                         ▼
         │  VoteFeedback  │◀── X-Session-ID response hdr ── ┌────────────────────┐
         └────────────────┘                                  │ FastAPI            │
                  ▲                                          │  routers/chat.py   │
                  │                                          │   │                │
                  │ session_id (React ref)                   │   ▼                │
                  │                                          │  pydantic-ai Agent │──▶ Bedrock (Claude)
                  │                                          │   (auto-instr.)    │
                  └──────── future signals ──────────────────│   Kelet traces ────┼──▶ console.kelet.ai
                                                             └────────────────────┘
                                                                      │
                                                                      ▼
                                                                    Redis
                                                              (session UUID, 30m TTL)
```

### Project map

```
Use case: RAG docs Q&A chatbot (BM25 over llms.txt)
Flows → Kelet projects:
  - docs Q&A → project "docs-ai-react-eval"
User-facing: yes
Stack: FastAPI + pydantic-ai (server), React 18 + Vite (client)
Config: .env (server), frontend/.env (Vite)
Deployment: Vercel (frontend) + Fly.io (backend) + existing k8s chart
Mode: full
```

## Checkpoint 1 — Mapping confirmation

`📍  Analysis ✅ → Checkpoint 1 🔄 → Signal Analysis ○ → Checkpoint 2 ○ → impl ○`

**[AskUserQuestion #1]** "Does this diagram, map, and workflow summary accurately represent your system? Anything I missed? (The repo has no React today — I'd scaffold a minimal Vite + TS + React 18 chat UI under `frontend/` and wire VoteFeedback there. Plain chat UI, nothing fancy.)"

**Developer:** Confirmed mapping. Confirmed: yes, scaffold React frontend under `frontend/`.

## Signal Analysis Pass (internal)

Silently reasoned — only results surface below.

- Synthetic candidates, filtered by "what traces already have vs what they can't":
  - **Task Completion** (Usefulness) — anchor evaluator.
  - **Answer Relevancy** (Comprehension) — off-topic responses, missed question.
  - **RAG Faithfulness** (Correctness, retrieval-grounded) — agent does `search_docs` + `get_page`, so traces have retrieval steps to compare the answer against. Direct fit.
  - Skipped `Hallucination Detection` — overlaps RAG Faithfulness when a retrieval step exists. One evaluator per category.
  - Skipped `Session Health Stats` — traces already expose turn / token counts.
- Coded signals (frontend): propose **VoteFeedback** (👍/👎) since we're adding the UI anyway. No edits (plain chat, no AI-generated form values) and no retry button yet — skip both for lightweight.

## Checkpoint 2 — Confirm plan + collect inputs

`📍  Analysis ✅ → Checkpoint 1 ✅ → Signal Analysis ✅ → Checkpoint 2 🔄 → impl ○`

**Plan preview:**

- Server: `import kelet` and `kelet.configure(api_key=settings.kelet_api_key, project=settings.kelet_project)` in `app/main.py` at module scope — before the FastAPI app is created, once per process. pydantic-ai is auto-instrumented, so **no `agentic_session()` wrapper is required**. SDK errors are silenced — build passing is not evidence.
- Config: add `KELET_API_KEY` + `KELET_PROJECT` to `.env` / `.env.example` (secret key is server-only; never bundled in the frontend).
- Frontend: scaffold `frontend/` with Vite + TS + React 18, minimal chat UI (textarea + send + message list). Wrap root in `KeletProvider`; read `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT` from `import.meta.env`. Propagate `X-Session-ID` from the POST response into a `useRef`, pass it to `<VoteFeedback.Root session_id={...}>` below each AI message. Use direct-children (not render-prop) pattern — `VoteFeedback.UpvoteButton` already owns its `<button>`.
- Synthetics: auto-create the three evaluators you pick via `POST /api/projects/docs-ai-react-eval/synthetics` with your secret key.

**What you'll see**

| After implementing                          | Visible in Kelet console                                  |
| ------------------------------------------- | --------------------------------------------------------- |
| `kelet.configure()` (server)                | LLM spans in Traces: model, tokens, latency, errors       |
| VoteFeedback (React)                        | Signals: 👍/👎 correlated to the exact trace via session_id |
| Platform synthetics (3 evaluators)          | Signals: automated quality scores per session             |

**[AskUserQuestion #2 — multiSelect]** Combined question: evaluator picks + plan approval + keys + project + key mode.

**Developer:**
- Evaluators: selected `Task Completion`, `Answer Relevancy`, `RAG Faithfulness`.
- Plan approved.
- `KELET_API_KEY = sk-kelet-eval-test`
- `VITE_KELET_PUBLISHABLE_KEY = pk-kelet-eval-test`
- Project: `docs-ai-react-eval`
- Key mode: **Paste secret key**.

## Creating the evaluators

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) — Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

Executed (verbatim):

```bash
curl -sS --max-time 360 \
  -X POST "http://localhost:8765/api/projects/docs-ai-react-eval/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"RAG docs Q&A chatbot answering questions about Kelet product docs via BM25 search over llms.txt","ideas":[{"id":"task-completion","name":"Task Completion","description":"Did the agent accomplish the user'\''s documentation question, or did it deflect / leave intent unaddressed?","evaluator_type":"llm"},{"id":"answer-relevancy","name":"Answer Relevancy","description":"Is the answer on-topic for the user'\''s docs question, without padding or drift to unrelated pages?","evaluator_type":"llm"},{"id":"rag-faithfulness","name":"RAG Faithfulness","description":"Do the claims in the answer match the retrieved doc pages, or does the agent contradict / extrapolate beyond the source?","evaluator_type":"llm"}]}'
```

Note: `https://api.kelet.ai` substituted with `http://localhost:8765` per eval environment override.

**Response:**

```
created=3 updated=0 failed=0 deduped=false
200
```

`✅ Kelet is now watching docs-ai-react-eval. First evaluator results in ~3min at https://console.kelet.ai/docs-ai-react-eval/signals`

## Implementation (executed)

`📍  Analysis ✅ → Checkpoint 1 ✅ → Signal Analysis ✅ → Checkpoint 2 ✅ → impl 🔄`

### Server

- **`app/main.py`** — added `import kelet` and `kelet.configure(api_key=settings.kelet_api_key, project=settings.kelet_project)` at module scope. Pass values explicitly because pydantic-settings hydrates `.env` into `settings.*` but does NOT inject into `os.environ` — so the no-args form would silently miss them when only `.env` is used. Comment recorded in the file.
- **`.env`** — set `KELET_API_KEY=sk-kelet-eval-test`, `KELET_PROJECT=docs-ai-react-eval`. `.env` is already gitignored.
- **`.env.example`** — documented both vars with a pointer to `console.kelet.ai/api-keys`.

### Frontend (new `frontend/` tree)

- `package.json` — React 18, Vite 5, TypeScript 5, `@kelet-ai/feedback-ui ^1.3.0`.
- `vite.config.ts` — dev proxy `/chat → http://localhost:8001` so the SPA and FastAPI share an origin locally.
- `tsconfig.json`, `index.html`, `src/vite-env.d.ts`.
- `src/main.tsx` — `<KeletProvider apiKey={VITE_KELET_PUBLISHABLE_KEY} project={VITE_KELET_PROJECT}>` wrapping the app.
- `src/App.tsx` — minimal chat UI (textarea + send + SSE-streamed message list). Captures `X-Session-ID` from the POST response into a `useRef`, re-sends it on follow-ups, and passes it to `<VoteFeedback.Root session_id={...}>` below each AI message. Uses direct-children pattern for `UpvoteButton` / `DownvoteButton` — no nested buttons.
- `src/styles.css` — dark, minimal palette matching the "plain chat UI" brief. No emoji-default styling; feedback buttons reuse the app's `--panel-2` / `--border` / `--accent` tokens.
- `.env` — `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test`, `VITE_KELET_PROJECT=docs-ai-react-eval`. `.gitignore` excludes it.
- `.gitignore` — `node_modules`, `dist`, `.env`.

## Phase V — Verification

- Every agentic entry point is covered: pydantic-ai is auto-instrumented, single flow, configure() is module-scope.
- Session ID is consistent end-to-end: server `uuid.uuid4()` → Redis → `X-Session-ID` response header → React `useRef` → `VoteFeedback.Root session_id=`.
- `configure()` runs once at startup, not per-request.
- Secret key is server-only (`.env` + `settings.kelet_api_key`); publishable key is the only value exposed to the Vite bundle.
- `document.querySelectorAll('button button').length === 0` — `VoteFeedback.UpvoteButton` / `DownvoteButton` are rendered with direct children (an emoji text node), so there is no nested `<button>` inside them. No render-prop pattern used.
- Smoke test: start the FastAPI server → `npm install && npm run dev` in `frontend/` → ask a docs question → open `https://console.kelet.ai/docs-ai-react-eval/traces` and confirm spans appear (allow a few minutes); give 👍/👎 and confirm the signal arrives on the same session.

Done.
