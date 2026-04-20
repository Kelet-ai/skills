# Kelet Integration Skill — Transcript

**Eval:** #5 `expand-to-full-mode`
**Repo:** `/Users/almogbaku/projects/kelet/docs-ai` (branch `main`)
**Developer prompt:** "I want to go deeper with Kelet — add more signals and get better coverage"
**Pre-existing state:** `kelet.configure()` + `kelet.agentic_session()` + `kelet.shutdown()` already wired.

---

## Welcome

🕵️  Welcome to Kelet — your AI detective

Kelet is a reasoning agent that ingests traces + signals, clusters failures, suggests fixes.

- **Trace = the scene.** Every LLM call + tool use auto-recorded after `kelet.configure()`.
- **Signal = the tip.** 👎, edit, abandon — points the detective at something worth investigating. Not a verdict.
- **Synthetic = forensic tools.** Automated signals from trace data. No code.
- **Session = the case file.** Traces grouped by one unit of work.
- **Project = the jurisdiction.** One per agentic use case.

I can see Kelet is already wired — `configure`, `agentic_session`, and `shutdown` are in place. Since you want to go deeper, I'll switch to **full mode**: add layered failure-mode signals and a broader synthetic evaluator set.

```
📍  Mapping 🔄 → Signals ○ → Plan ○ → Implement ○ → Verify ○
```

---

## 🗺️  MAPPING

### Architecture

```
Browser / curl
      │   POST /chat  { message, session_id?, current_page_slug? }
      │   GET  /chat  ?q=...         (stateless, one-shot)
      ▼
┌─────────────────────────────── FastAPI (app/main.py) ───────────────────────────────┐
│  lifespan: kelet.configure(api_key, project=kelet_project)                          │
│            docs_cache.start()                                                       │
│            ...                                                                      │
│  finally:  kelet.shutdown()   ← BatchSpanProcessor flush                            │
│                                                                                     │
│  CORSMiddleware (exposes X-Session-ID)                                              │
│                                                                                     │
│  routers/chat.py:                                                                   │
│    POST /chat                                                                       │
│      ├─ rate-limit (Redis)                                                          │
│      ├─ resolve / create ChatSession (Redis, 30m TTL, server-owned UUID)            │
│      │    session_id travels → response header X-Session-ID                         │
│      ├─ async with kelet.agentic_session(session_id=session.session_id):            │
│      │    pydantic-ai agent.iter() → SSE stream                                     │
│      │    tools: search_docs (BM25), get_page                                       │
│      │    docs index from DOCS_LLMS_URLS                                            │
│      └─ persist updated history back to Redis                                       │
│                                                                                     │
│    GET /chat (stateless) — no session, one-shot plain text                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Project Map

```
Use case: Kelet docs Q&A assistant (RAG over kelet.ai llms.txt)
Flows → Kelet projects:
  - flow "docs_ai" → project "docs_ai"  (via env: kelet_project, default "docs_ai")
User-facing: yes (chat), also a server-to-server GET /chat
Stack: FastAPI + pydantic-ai (Bedrock Claude Sonnet 4.6) + Redis sessions
Config: pydantic-settings → .env (KELET_API_KEY server-only; no React, no publishable key)
Deployment: k8s/ + docker-compose.yml + Dockerfile (multi-env hints — k8s manifests present)
Mode: full (developer explicitly asked to go deeper)
```

### Session semantics — already correct

`ChatSession.session_id` is a server-generated UUID (cache/__init__.py:22). New UUID on missing/expired lookup, passed to `agentic_session(session_id=...)`, surfaced on `X-Session-ID`. Matches the "app owns the session ID" case; correctly wrapped already. No user identity is attached — no PII risk.

### Anti-pattern found in current code

`src/routers/chat.py` (lines 30-34, 45, 48-57) runs a **coded rephrase detector** using `message.lower().startswith(_REPHRASE_PREFIXES)` and fires a `FEEDBACK` signal with `trigger_name="user-correction"`.

This is a known anti-pattern — prefix matching misses the majority of rephrases (reworded without a keyword, where most of the diagnostic value lives) and fires on innocent clarifications ("actually, I think…"). Rephrase detection must live as an **LLM synthetic evaluator** on the trace, not as a coded signal.

**Proposed fix:** remove the `_REPHRASE_PREFIXES` block; replace with the `Conversation Completeness` / `Sentiment Analysis` / a custom "user re-asked" synthetic evaluator that scores the *preceding* turn.

---

## Checkpoint 1 — AskUserQuestion (mapping confirmation)

**Question:** "Does this diagram, project map, and workflow summary accurately represent your system? I also want to flag: there's a coded rephrase detector in `chat.py` that's the wrong layer for rephrase detection — I'll propose replacing it with an LLM synthetic. OK to proceed?"

**Simulated developer answer:** confirm. "Yes, replace with LLM synthetic."

```
✅  Mapping
📍  Signals 🔄 → Plan ○ → Implement ○ → Verify ○
```

---

## 🔎  SIGNALS

### Full-mode signal stack (what we'll add)

Since Kelet is already configured + session-wrapped, every span is already captured. Full mode means layering failure-mode coverage across three planes: **trace-side synthetics**, **server-side coded events** for behaviors the platform can't see, and **removal of the anti-pattern**.

#### Proposed synthetic evaluators (managed, zero code)

One per failure category, no overlap — chosen for this RAG + docs Q&A agent:

1. **Task Completion** (llm, universal) — Did the agent actually answer the user's question? Catches silent refusals, deflected asks, off-topic drift. Anchor for the project.
2. **RAG Faithfulness** (llm, RAG) — Did the answer stay grounded in retrieved docs (`search_docs` + `get_page` output)? Catches context-specific hallucination — the primary failure mode for a docs assistant.
3. **Hallucination Detection** (llm, general) — Fabricated product names, invented APIs, nonexistent pages. Catches cases where retrieval *missed* and the model filled the gap.
4. **Sentiment Analysis** (llm, multi-turn) — User frustration across the session. This is the correct layer for what the coded rephrase detector was *trying* to do — catches repeated corrections, reworded asks, dissatisfaction, without keyword matching.
5. **Tool Usage Efficiency** (llm, multi-tool) — Was `search_docs` used when `get_page` would have been direct? Redundant searches, wasted turns.
6. **Session Health Stats** (code, structural) — Turn counts, token usage, tool-call frequency. Free structural anomaly detection — does not overlap with the llm evaluators.

Together these cover: comprehension, execution, correctness, usefulness, user reaction. No double coverage.

#### Proposed server-side coded signals (only what traces can't see)

Server-only app → no React → no VoteFeedback / useFeedbackState. Every signal below is tied to an **explicit** trigger, never inferred from message text:

- **Rate-limit exhaustion** (`EVENT`, `HUMAN`, `trigger_name="user-rate-limited"`) — user tried to continue but got 429. Signals a friction point that the trace alone hides (the 429 skips the agent entirely).
- **Tool-call failure** (`EVENT`, `HUMAN`, `trigger_name="tool-error"`) — docs_loader page/search miss raises → emits one signal per failed tool call before the response degrades silently.
- **Session-history persistence failure** (`EVENT`, `HUMAN`, `trigger_name="session-persist-error"`) — Redis write failed after agent ran. Next turn loses history silently; Kelet console shows the break.
- **Agent stream error** (`EVENT`, `HUMAN`, `trigger_name="agent-stream-error"`) — exception during SSE. Already logged; adding a signal ties the failure to the exact trace.

Abandon / retry aren't applicable here — there's no abandon button, no timeout SLA, no explicit retry API. Not inferring from message text (that's the anti-pattern).

#### Anti-pattern to REMOVE

Remove `_REPHRASE_PREFIXES` prefix list + the coded `kelet.signal(FEEDBACK, HUMAN, "user-correction")` branch in `_run_agent_stream`. Rephrase detection moves to the `Sentiment Analysis` synthetic evaluator. No replacement coded signal.

---

## Checkpoint 2 — Plan + Inputs

### Complete plan

**No changes to existing integration** — `configure()` / `agentic_session()` / `shutdown()` stay exactly as they are.

1. **Remove anti-pattern** in `src/routers/chat.py`:
   - Delete `_REPHRASE_PREFIXES` tuple.
   - Delete the `is_rephrase` block and the associated coded `kelet.signal(...)` call.

2. **Add server-side coded signals** (gated on `settings.kelet_api_key`):
   - Tool wrappers in `src/agent/__init__.py` to emit `tool-error` on exceptions from `search_docs` / `get_page`.
   - Rate-limit emission in POST `/chat` + GET `/chat` just before raising 429 — emits `user-rate-limited`.
   - Session-persist failure branch in `_run_agent_stream` — emits `session-persist-error` instead of silent `logger.warning`.
   - Agent stream error branch — emits `agent-stream-error` from the `except Exception` path.

3. **Create synthetic evaluators via API** — 6 selected above, project `docs-ai-iter8-expand`.

4. **Write `KELET_API_KEY` + `KELET_PROJECT`** to `.env` (already has `DOCS_*` keys). `.env` is in `.gitignore`.

### "What you'll see" table

| After implementing                                    | Visible in Kelet console                                                    |
| ----------------------------------------------------- | --------------------------------------------------------------------------- |
| Existing `kelet.configure()` + `agentic_session()`    | LLM spans + grouped sessions (already working once key is set)              |
| New coded signals (rate-limit / tool / persist / stream) | Signals view: each failure tied to exact trace, no inference                |
| 6 synthetic evaluators                                | Automated quality scores per session — comprehension → correctness → usefulness |
| Removed rephrase detector                             | No false positives; rephrase/frustration captured correctly by Sentiment synthetic |

### AskUserQuestion (slot 2)

Single multi-select covering:

1. **Which synthetic evaluators to create?** — `Task Completion`, `RAG Faithfulness`, `Hallucination Detection`, `Sentiment Analysis`, `Tool Usage Efficiency`, `Session Health Stats`, or `None`.
2. **Plan approval**.
3. **Project name** (create first at console.kelet.ai → New Project).
4. **API key mode**: Paste secret / I'll grab one / Can't paste.

**Simulated developer answer:** pick all 6 synthetic evaluators, approve plan, project = `docs-ai-iter8-expand`, key mode = "Paste secret key", `sk-kelet-eval-test`.

```
✅  Mapping
✅  Signals
📍  Plan 🔄 → Implement ○ → Verify ○
```

---

## 🧾  PLAN

(Presented to developer, `ExitPlanMode` approved — proceeding to IMPLEMENT.)

---

## 🛠️  IMPLEMENT

(See `changes.diff` for exact diff.)

Steps performed:

1. Removed `_REPHRASE_PREFIXES` + coded rephrase signal from `src/routers/chat.py`.
2. Added `user-rate-limited` signal emission in both POST and GET `/chat` handlers before 429.
3. Added `tool-error` emission around `search_docs` / `get_page` tool bodies in `src/agent/__init__.py`.
4. Added `session-persist-error` and `agent-stream-error` signal emissions inside `_run_agent_stream`.
5. Wrote `KELET_API_KEY=sk-kelet-eval-test` and `KELET_PROJECT=docs-ai-iter8-expand` to `.env`.
6. Created 6 synthetic evaluators via `POST /api/projects/docs-ai-iter8-expand/synthetics`.

### Synthetic creation (Bash-executed)

> ⏳ Creating your evaluators. This takes **1–3 minutes** (sometimes up to 5) — Kelet generates each config with an LLM and runs a dedup pass. Sit tight; don't cancel.

(curl output recorded below)

```
✅  Mapping
✅  Signals
✅  Plan
📍  Implement 🔄 → Verify ○
```

---

## ✅  VERIFY

- Every agentic entry point still covered — no changes to `configure()` / `agentic_session()` / `shutdown()`.
- `kelet.shutdown()` still in `lifespan` `finally:` block (preserved verbatim).
- Secret key written to server `.env` only; no frontend, no publishable key.
- New signals gated on `settings.kelet_api_key` — silent no-op when unset.
- Rephrase anti-pattern removed; no `startswith` detector remains.
- Tool-call failure surface now instrumented (was previously invisible outside logs).
- Smoke test: `curl -X POST http://localhost:8001/chat -d '{"message": "hello"}'` → open `https://console.kelet.ai/docs-ai-iter8-expand` → confirm session + signals appear (allow a few minutes).

```
✅  Mapping
✅  Signals
✅  Plan
✅  Implement
✅  Verify
```

Done. Your docs-ai assistant now has full signal coverage: trace-side synthetics across all quality dimensions, coded events for behaviors the platform can't observe, and the rephrase anti-pattern replaced by the correct layer.
