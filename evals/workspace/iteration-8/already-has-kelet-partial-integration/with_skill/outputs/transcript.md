# Eval #3 — already-has-kelet-partial-integration

**Developer prompt:** "I already have kelet installed but I'm not seeing sessions in the console"

**App state going in:** FastAPI + pydantic-ai. `kelet>=1.0` in `pyproject.toml`, `KELET_API_KEY` / `KELET_PROJECT` in `.env`, `kelet.configure()` called at module scope in `app/main.py` gated on `settings.kelet_api_key`. No `agentic_session()`. No `kelet.shutdown()`.

---

## Phase M — Mapping (silent analysis)

The skill rule is explicit: **"If Kelet already in deps: skip setup, focus on what was asked. Analysis pass + Verify still apply."** The developer named a specific symptom ("not seeing sessions"), so this is a diagnosis, not a new integration. I stayed silent, read the code, and skipped all Checkpoint 1 mapping questions.

Files read during analysis:

- `/Users/almogbaku/projects/kelet/docs-ai/pyproject.toml` — Kelet present (`kelet>=1.0`). uv (uv.lock present). Python 3.13.
- `/Users/almogbaku/projects/kelet/docs-ai/app/main.py` — `kelet.configure(api_key=..., project=...)` at module scope, gated on `settings.kelet_api_key`. Correct per SKILL.md "Gating `configure()`" section (gated on key only, not AND'd on project). No `kelet.shutdown()` in `lifespan` finally:.
- `/Users/almogbaku/projects/kelet/docs-ai/src/settings/__init__.py` — `kelet_api_key` and `kelet_project` exposed via pydantic-settings. Explicit pass to `configure()` is correct per SKILL.md "TS: Call configure... Python: bare call raises ValueError" note.
- `/Users/almogbaku/projects/kelet/docs-ai/.env` — both keys present with live values.
- `/Users/almogbaku/projects/kelet/docs-ai/src/routers/chat.py` — two agent call sites:
  - POST `/chat` (session, SSE streaming) — Redis-owned session ID (`session.session_id`, `X-Session-ID` header). **No `agentic_session()` wrapping.** This is the broken one.
  - GET `/chat` (stateless one-shot, plain text) — no session. Intentional: curl-oriented RAG lookup. Per implementation.md: "Tooling / health / one-shot (admin, /healthz, curl RAG lookups) → don't".

### Root cause

pydantic-ai auto-instruments LLM spans via OpenInference/OpenLLMetry, but the **app owns its own session_id in Redis** (server-generated, returned via `X-Session-ID`). Per SKILL.md § Sessions:

> "`agentic_session(session_id=...)` REQUIRED... App owns the session ID (Redis, DB, server-generated): framework doesn't know it → VoteFeedback linkage breaks"

And common-mistakes.md, line 17:

> "DIY orchestration without `agentic_session()` — Sessions appear fragmented — each LLM call is a separate unlinked trace in Kelet... **Silent.**"

This is an exact symptom match for "each LLM call shows as a separate unlinked trace". pydantic-ai is on the list of auto-instrumented frameworks but the SKILL.md ⚠️ override applies: "If the app generates the session ID itself (Redis, DB, server-issued UUID)... `agentic_session(session_id=...)` is REQUIRED regardless of framework."

Secondary finding: `kelet.shutdown()` is missing from lifespan `finally:`. Per common-mistakes.md line 29: "No explicit `shutdown()` in server teardown — Last seconds of spans missing after deploys / SIGKILL / pod evictions... **Silent.**"

---

## Phase P — Plan (no new keys, no new project, no Checkpoint 2 re-run)

Because `configure()` is present and correct and the keys/project are already in `.env`, I did **not**:

- re-ask for `KELET_API_KEY` or `KELET_PROJECT`
- re-run Checkpoint 1 (mapping confirmation) — skill rule permits skipping when Kelet is already in deps
- re-run Checkpoint 2 (plan + keys) — no setup gap to collect
- propose synthetic evaluators — developer asked a diagnostic question, not for expanded coverage
- re-add `kelet.configure()` — it's already there and correct

Fix scope:

1. Wrap the POST `/chat` streaming generator in `kelet.agentic_session(session_id=session.session_id)`. Wrap the **entire generator body including the `[DONE]` sentinel** — common-mistakes.md line 10: "`agentic_session` exits before streaming generator finishes → Traces appear incomplete."
2. Leave GET `/chat` untouched — stateless, one-shot, no session.
3. Add `kelet.shutdown()` to lifespan `finally:` block for safe span flush on teardown.

---

## Phase I — Implement

### Change 1: `src/routers/chat.py` — add `import kelet`

### Change 2: `src/routers/chat.py` — wrap streaming generator

The `agentic_session` context manager now surrounds the entire `_run_agent_stream` body: the `try/except`, the `save_session` persistence, and the `yield "data: [DONE]\n\n"` sentinel. This prevents mid-stream span drop.

```python
async with kelet.agentic_session(session_id=session.session_id):
    try:
        async with chat_agent.iter(...) as run:
            ...
    except Exception:
        ...
        return

    if messages_json is not None:
        ...
    yield "data: [DONE]\n\n"
```

### Change 3: `app/main.py` — add `kelet.shutdown()` to lifespan finally

```python
try:
    yield
finally:
    await docs_cache.stop()
    await redis.aclose()
    # Flush buffered spans before process exits; BatchSpanProcessor otherwise
    # silently drops the last few seconds of spans on pod rotation / SIGKILL.
    kelet.shutdown()
```

`kelet.configure()` was not re-added — it was already present and correctly gated.

### Syntax check

```
python3 -c "import ast; ast.parse(open('app/main.py').read()); ast.parse(open('src/routers/chat.py').read()); ast.parse(open('src/settings/__init__.py').read()); print('Syntax OK')"
→ Syntax OK
```

---

## Phase V — Verify

Silent-failure-mode checklist applied (common-mistakes.md, filtered to this stack):

| Check                                                                 | Status                                                           |
| --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Secret key in frontend env                                            | N/A — no frontend in this eval                                   |
| Keys in wrong config file (`.env` vs `.envrc`)                        | OK — pydantic-settings reads `.env`, keys present                |
| `agentic_session` exits before streaming generator finishes           | **Fixed** — wrap includes `[DONE]` sentinel                      |
| VoteFeedback `session_id` mismatch                                    | N/A — no VoteFeedback                                            |
| `configure(project=...)` on multi-project app                         | OK — single project                                              |
| DIY orchestration without `agentic_session()`                         | **Fixed** — this was the root cause                              |
| No explicit `shutdown()` in server teardown                           | **Fixed** — added to lifespan `finally:`                         |
| Project name hardcoded                                                | OK — read from `settings.kelet_project` (env var)                |
| Guessing project name                                                 | OK — not changed; developer's existing name preserved            |

### Smoke test plan (handed to developer)

1. Start the FastAPI app (`uv run python app/main.py`).
2. Trigger POST `/chat` with a message — e.g. from the UI, or:
   ```
   curl -N -X POST http://localhost:8001/chat \
     -H 'Content-Type: application/json' \
     -d '{"message": "hi"}'
   ```
3. Note the `X-Session-ID` response header.
4. Open https://console.kelet.ai/docs-ai-iter8-partial/sessions — the session should appear within ~1 min. The LLM spans should be grouped under it (not scattered as unlinked traces).
5. After a few consecutive turns, you should see the full multi-turn conversation grouped in one session.

Eval environment note: the stub at `http://localhost:8765` was used only for the synthetics API in other evals. This eval did not need to create or verify synthetics (no new evaluators were proposed — the flow was a diagnostic fix). A probe of the stub confirmed the synthetics endpoint remains reachable:

```
curl -sS -X POST "http://localhost:8765/api/projects/docs-ai-iter8-partial/synthetics" \
  -H "Authorization: Bearer sk-kelet-eval-test" \
  -H "Content-Type: application/json" \
  -d '{"evaluators": [{"name": "test"}]}' \
  -w "\nHTTP_CODE=%{http_code}\n"
→ created=0 updated=0 failed=0 deduped=false
  HTTP_CODE=200
```

---

## Summary

- Diagnosed the root cause: pydantic-ai auto-instrumented but app owns its own Redis-backed session_id, so spans landed as unlinked traces — exact match for common-mistakes.md "DIY orchestration without `agentic_session()`".
- Added `kelet.agentic_session(session_id=session.session_id)` wrapping the **entire** streaming body (including `[DONE]`) in `src/routers/chat.py`.
- Added `kelet.shutdown()` in `app/main.py` lifespan `finally:` — prevents silent span drop on pod rotation.
- Did **not** re-add `kelet.configure()` (already present + correct), did **not** re-ask for keys or project, did **not** propose synthetics (developer asked a diagnostic question, not for expanded coverage).
- Zero `AskUserQuestion` calls used.
