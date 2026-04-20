# Questions Asked (AskUserQuestion calls)

Budget: ≤3 (ideally 2). Used: **2**.

---

## 1. Checkpoint 1 — Mapping confirmation (combined with anti-pattern flag)

**Prompt:** "Does this diagram, project map, and workflow summary accurately represent your system? I also want to flag: there's a coded rephrase detector in `chat.py` (`_REPHRASE_PREFIXES` + `startswith`) that's the wrong layer for rephrase detection — I'll propose replacing it with an LLM synthetic evaluator. OK to proceed on both fronts?"

**Simulated developer answer:** "Confirm. Yes, replace with LLM synthetic."

---

## 2. Checkpoint 2 — Plan approval + synthetic selection + keys + project name (single multi-select)

**Prompt (single question, four fields):**

1. Which of these synthetic evaluators should I create?
   - Task Completion
   - RAG Faithfulness
   - Hallucination Detection
   - Sentiment Analysis
   - Tool Usage Efficiency
   - Session Health Stats
   - None
2. Does the rest of the plan (remove coded rephrase detector, add 4 server-side coded signals for failure modes, keep existing `configure`/`agentic_session`/`shutdown` untouched) look right?
3. Project name (must already exist in the Kelet console):
4. API key mode: Paste secret / I'll grab one / I can't paste secrets here

**Simulated developer answer:**
- Evaluators: all 6 selected
- Plan approved
- Project: `docs-ai-iter8-expand`
- Key mode: Paste secret key → `sk-kelet-eval-test`

---

No third question was needed. Deployment pattern (`.env` via pydantic-settings, k8s manifests present) was inferred without asking; existing integration already handled secrets correctly.
