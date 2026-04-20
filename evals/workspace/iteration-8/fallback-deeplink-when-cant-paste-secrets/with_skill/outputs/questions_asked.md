# Questions Asked — Eval #6 (fallback-deeplink-when-cant-paste-secrets)

Two `AskUserQuestion` calls total (within the ≤3 budget, at the ideal of 2).

---

## Question 1 — Checkpoint 1: Mapping + multi-env

**Header:** "Confirm mapping + multi-env project split"

**Prompt:** "Does this diagram + project map + workflow summary accurately represent your system? Also: you deploy to prod + stag via Helm — one Kelet project across envs (simpler), one per env (non-prod noise isolated from prod traces), or I got something wrong?"

**Options (multiSelect: false):**
- Looks right — one project across envs
- Looks right — split into per-env projects (prod + stag)
- Needs changes (describe below)
- Other

**Simulated answer:** "Looks right — one project across envs"

---

## Question 2 — Checkpoint 2: Evaluators + plan + project + key mode

**Header:** "Pick evaluators, approve plan, set project + key mode"

**Prompt (multiSelect where noted):**

**A. Proposed synthetic evaluators** (multiSelect: true) — Kelet platform manages these, zero code:
- [x] Task Completion (llm) — did the agent answer what was asked
- [x] Answer Relevancy (llm) — on-topic, no padding or deflection
- [x] RAG Faithfulness (llm) — stays faithful to search_docs / get_page output
- [x] Hallucination Detection (llm) — fabricated APIs / citations not in scanned docs
- [x] Conversation Completeness (llm) — multi-turn intents addressed
- [ ] None

**B. Plan approval:**
- Approve as-is
- Approve with changes (describe)
- Redo

**C. Project name** (create at https://console.kelet.ai first — wrong name = silent routing to nowhere):
- *free-text → `docs-ai-iter8-fallback`*

**D. API key mode:**
- Paste secret key (sk-kelet-...) — auto-create evaluators now (primary)
- I'll grab one — halt until pasted
- **I can't paste secrets here** — deeplink fallback (no project verification)

**Simulated answers:**
- Evaluators: all 5 (Task Completion, Answer Relevancy, RAG Faithfulness, Hallucination Detection, Conversation Completeness)
- Plan: Approve as-is
- Project: `docs-ai-iter8-fallback`
- API key mode: **"I can't paste secrets here"** → deeplink fallback (no curl to auto-create endpoint)

---

**Question budget:** 2 of ≤3 used. Slot 3 intentionally not consumed — deployment was already identified from `k8s/charts/docs-ai/` and `k8s/environments/{prod,stag}.yaml`, and the developer declined to paste a secret so no secret-management dialog was needed.
