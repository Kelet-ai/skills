# AskUserQuestion calls — eval #7 (wrong-project-name-surfaces-404-hint)

Total: **3** (at the budget ceiling of 3).

---

## #1 — Checkpoint 1: Mapping confirmation

**Question:** "Does this diagram, map, and workflow summary accurately represent your system?
If you ship to multiple envs (prod + stag), do you want one Kelet project across envs, or
one per env?"

**Options:**

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
- [x] RAG Faithfulness — claims grounded in BM25-retrieved docs (`search_docs` + `get_page` tools)
- [ ] None

**Developer answer:** all three selected.

**Part B — Plan approval:**

- [x] Plan looks right — proceed.

**Part C — Keys + project name:**

- `KELET_API_KEY`: `sk-kelet-eval-test`
- Project name: **`not-a-real-project`** (deliberately invalid per eval spec)
- No publishable key needed (no React / VoteFeedback).

**Part D — API key mode:**

- [x] Paste secret key (sk-kelet-...) → primary auto-create path.
- [ ] I'll grab one
- [ ] I can't paste secrets here

**Developer answer:** paste secret → `sk-kelet-eval-test`.

---

## #3 — 404 recovery (triggered by `project_not_found` from the primary curl)

**Context:** primary curl returned `404 project_not_found` for `not-a-real-project`. Server
hint surfaced verbatim ("Create it first at console.kelet.ai → New Project, then re-run.").
Skill does not silently give up and does not blindly retry — asks what to do next.

**Question:** "The project `not-a-real-project` doesn't exist in your Kelet workspace. What
do you want to do?"

**Options:**

- [x] Re-enter a corrected project name — you already created one at the console.
- [ ] Halt — I need to create the project first (go to console.kelet.ai → New Project, then re-run the skill).
- [ ] Try a different project name from memory (same path as option 1).

**Developer answer:** *Re-enter a corrected project name* → **`docs-ai-iter8-recovered`**.

Skill updated `.env` (`KELET_PROJECT=docs-ai-iter8-recovered`) and re-ran the same curl
(only the project in the URL changed). Got `200 created=3 updated=0 failed=0 deduped=false`
→ rendered the success banner.

---

## Budget check

3 of 3 allowed `AskUserQuestion` calls used. The third slot was consumed by the 404 recovery
prompt — a legitimate, unskippable fork; the eval explicitly tests this path. Two routine
slots + one recovery-driven slot = exactly at the ceiling, not over.
