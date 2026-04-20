# AskUserQuestion calls

Total: 3 (at the skill's cap; justified by the 401 recovery path).

## 1. Checkpoint 1 — Mapping confirmation

> Does this diagram, project map, and workflow summary accurately represent your system? Anything I missed?

Context surfaced:
- Single flow `chat` -> project `docs-ai-iter8-401`
- FastAPI + pydantic-ai + Redis-backed sessions (server-generated UUIDs)
- App owns the session_id -> `agentic_session(session_id=...)` is required regardless of pydantic-ai auto-instrumentation
- Fly.io deployment -> production secrets via `fly secrets set`
- No React frontend, so no VoteFeedback in scope

Simulated answer: confirmed.

## 2. Checkpoint 2 — Plan + inputs (multiSelect)

Combined question with four sub-sections:

1. **Proposed synthetic evaluators (multiSelect):**
   - [ ] Task Completion
   - [ ] RAG Faithfulness
   - [ ] Answer Relevancy
   - [ ] None
2. **Plan approval:** Does the rest of the plan look right?
3. **Project name:** (create in console top-nav first)
4. **API key mode:**
   - Paste secret key (`sk-kelet-...`)
   - I'll grab one
   - I can't paste secrets here

Simulated answers:
- Evaluators: Task Completion + RAG Faithfulness + Answer Relevancy (all three)
- Plan: approved
- Project name: `docs-ai-iter8-401`
- API key mode: Paste secret key -> `sk-typo-wrong`

## 3. Recovery re-prompt (after 401)

Triggered after the primary curl returned HTTP 401 `{"detail":"Not authenticated"}`.

> The Kelet API returned 401 Not authenticated for that key — it looks invalid (likely a typo). Secret keys are shaped `sk-kelet-...` with no whitespace. Paste a corrected `KELET_API_KEY` to retry. I'm not falling back to the deeplink — you intended to paste a key, so let's retry properly.

Simulated answer: `sk-kelet-eval-test` -> re-ran the curl -> 200 -> success banner.
