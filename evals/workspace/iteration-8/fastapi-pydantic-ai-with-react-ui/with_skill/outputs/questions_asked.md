# Questions asked — eval #4

Budget: ≤3 `AskUserQuestion` calls. Ideal: 2. **Used: 2.**

---

## Q1 — Checkpoint 1: Mapping confirmation

**Prompt (single question, no sub-slots):**

> Does this diagram, map, and workflow summary accurately represent your system?
> Anything I missed?

**Options offered:** "Yes — looks right" · "No — let me correct something"

**Developer answer:** confirmed mapping.

---

## Q2 — Checkpoint 2: Plan + synthetics + keys + key mode (multiSelect, one call)

Bundled, per SKILL.md Checkpoint 2 rules. Single `AskUserQuestion` with `multiSelect: true`
and four sub-dimensions:

1. **Proposed synthetic evaluators** (multiSelect) — options:
   - Task Completion
   - RAG Faithfulness
   - Answer Relevancy
   - Sentiment Analysis
   - None

2. **Plan approval** — "Does the rest of the plan look right?"
   Options: "Approved" · "Needs changes"

3. **Project name** — confirmation of `docs-ai-iter8-react` as the project name.
   Options: "Use docs-ai-iter8-react" · "Use a different name"

4. **API key mode** (only because synthetic evaluators were selected):
   - Paste secret key (sk-kelet-...)
   - I'll grab one (halt)
   - I can't paste secrets here (deeplink fallback)

**Developer answered:**

- Synthetics: all four (Task Completion, RAG Faithfulness, Answer Relevancy,
  Sentiment Analysis).
- Plan: approved.
- Project: `docs-ai-iter8-react`.
- Key mode: **Paste secret key** → pasted `sk-kelet-eval-test`.

**Follow-up (not a new `AskUserQuestion` call — collected alongside Q2 per SKILL.md
rule about bundling keys + project name together at Checkpoint 2):** publishable key
`pk-kelet-eval-test`.

---

## Slot 3 — not used

Reserved for "deployment unknown AND secrets can't be safely handled" scenario. Not
triggered — developer described deployment (Vercel + Fly.io) in the initial prompt and
chose to paste the secret key, so no follow-up needed.

---

## Total

**2 `AskUserQuestion` calls.** Within the ideal 2-call target.
