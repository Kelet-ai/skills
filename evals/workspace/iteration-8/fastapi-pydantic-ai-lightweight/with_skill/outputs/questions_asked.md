# AskUserQuestion calls — eval #1 (fastapi-pydantic-ai-lightweight)

Total: **2** (within the ideal budget of 2).

---

## #1 — Checkpoint 1: Mapping confirmation

**Question:** "Does this diagram, map, and workflow summary accurately represent your system? If you ship to multiple envs (prod + stag), do you want one Kelet project across envs, or one per env?"

**Options (multiSelect-style; single answer expected):**

- "Yes, looks right (single project for now)"
- "Yes, looks right — but split per env (prod vs stag)"
- "No, something's off — let me correct it"

**Developer answer:** "Yes, looks right." (single project for now — map and diagram accepted.)

---

## #2 — Checkpoint 2: Plan + synthetics + keys + key mode

Bundled as a single `AskUserQuestion` with `multiSelect: true`, structured per the skill.

**Part A — Proposed synthetic evaluators (multiSelect):**

- [x] Task Completion — universal "did the agent answer the user's goal?"
- [x] Conversation Completeness — catches deflected/unaddressed intents across multi-turn chat
- [x] RAG Faithfulness — claims grounded in BM25-retrieved docs (agent has `search_docs` + `get_page` tools)
- [ ] None

**Developer answer:** all three selected.

**Part B — Plan approval:**

- [x] Plan looks right — proceed.

**Part C — Keys + project name:**

- `KELET_API_KEY`: `sk-kelet-eval-test`
- Project name: `docs-ai-iter8` (developer already created it at console.kelet.ai)
- No publishable key needed (no React / VoteFeedback).

**Part D — API key mode:**

- [x] Paste secret key (sk-kelet-...) → primary auto-create path.
- [ ] I'll grab one
- [ ] I can't paste secrets here

**Developer answer:** paste secret → `sk-kelet-eval-test`.

---

## Budget check

2 of the 3 allowed `AskUserQuestion` calls used. Third slot (deployment / secrets
escalation) was not needed: deployment identified (Fly.io) + developer pasted a key
directly, so no ambiguity remained.
