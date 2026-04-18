# Questions Asked by the Skill

Budget: at most 3 `AskUserQuestion` calls (ideally 2). Slot 3 spent on the 404 recovery question (server error response required input the skill couldn't infer) — deployment was already identifiable (Fly.io) so slot 3 wasn't otherwise needed.

---

## Q1 — Checkpoint 1: Mapping Confirmation

**Preamble (presented to developer):**
- ASCII architecture diagram: Browser → FastAPI `POST /chat` → `kelet.agentic_session(session_id=session.session_id)` → pydantic-ai `chat_agent.iter()` → BM25 search / page retrieval tools → Redis session store
- Project map: single flow, lightweight mode, pydantic-ai auto-instrumented, server-owned session ID (UUID, non-PII — no `user_id=` concern)
- Workflow summary: user asks docs question → BM25 search + page tools → streamed SSE answer; success = accurate on-topic answer grounded in docs, failure = off-topic / hallucinated slug / unanswered follow-up

**Question:** "Does this diagram, project map, and workflow summary accurately represent your system? Anything I missed?"

**Options presented:** `Looks right — proceed` · `Needs correction`

**Answer:** `Looks right — proceed`

---

## Q2 — Checkpoint 2: Plan Approval + Inputs

**Preamble (presented to developer):**
- Proposed lightweight plan: `kelet.configure()` in `app/main.py`, `kelet.agentic_session(session_id=session.session_id)` wrapping `chat_agent.iter()` in `_run_agent_stream()`, `.env` keys, Fly.io secret for prod
- No coded signals (no React frontend in this app → 0 coded signals, lightweight default)
- "What you'll see" table: configure → Traces; agentic_session → Sessions; Platform synthetics → Signals

**Question (multiSelect):**

1. **Proposed synthetic evaluators (pick which to create):**
   - [x] `Task Completion` (llm)
   - [x] `Answer Relevancy` (llm)
   - [x] `Conversation Completeness` (llm)
   - [ ] None
2. **Plan approval:** Does the rest of the plan look right? → `Approve`
3. **`KELET_API_KEY` (sk-kelet-...):** → `sk-kelet-eval-test`
4. **Project name (you must create it first at console.kelet.ai → New Project — wrong name = silent routing failure / 404):** → `not-a-real-project`
5. **API key mode:** → `Paste secret key (sk-kelet-...)` (primary auto-create path)

---

## Q3 — 404 Recovery (triggered by server response)

**Context:** After executing the primary synthetic-creation curl with project `not-a-real-project`, the server returned:

```
HTTP 404
{"detail": {"error": "project_not_found", "project": "not-a-real-project", "hint": "Create it first at console.kelet.ai → New Project, then re-run."}}
```

Surfaced verbatim to the developer — not swallowed. The skill did not proceed; it asked how to recover rather than silently aborting or retrying blindly.

**Question:** "The Kelet server returned **404 `project_not_found`** for `not-a-real-project` with this hint: *Create it first at console.kelet.ai → New Project, then re-run.* How do you want to proceed?"

**Options presented:**
- `Re-enter a corrected project name` (skill re-executes the curl with the new name)
- `I'll create the project in the console first, pause integration` (halt — re-run skill after)
- `Abort — I'll come back later`

**Answer:** `Re-enter a corrected project name` → `docs-ai-eval-recovered`

**Outcome:** Skill re-executed the exact same curl with the corrected project. Server returned 200, `created=3 updated=0 failed=0 deduped=false`. Integration continued to Phase V (verification checklist).
