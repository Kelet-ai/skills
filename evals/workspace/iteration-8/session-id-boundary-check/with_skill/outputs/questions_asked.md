# Questions Asked — eval #2 (session-id-boundary-check)

**Total AskUserQuestion calls:** 2 (budget: ≤3).

---

## Question 1 — Checkpoint 1: Mapping + session fix + multi-env

**When:** After silent analysis pass, as the single Checkpoint 1 `AskUserQuestion`.

**What was asked (conceptual):**
- Confirm the project map + architecture diagram represent the system.
- (a) Confirm proposed session-boundary fix: generate a UUID per conversation as `kelet_session_id` (not using the phone number, which outlives sessions).
- (b) One Kelet project across environments (staging/prod from k8s overlays) or one per env?

**Why:** Session-boundary decision materially affects every trace and can't be silently chosen. PII decision (phone number → omit `user_id=`) was deliberately NOT included as a question slot — per SKILL.md Sessions, obvious PII means "omit and call it out prominently", not "ask the developer".

**Simulated user answer:** "Yes, generate UUID per conversation." (interpreted as approval for the UUID fix.)

---

## Question 2 — Checkpoint 2: Plan + inputs

**When:** After signal analysis, at the single Checkpoint 2 combined `AskUserQuestion`.

**What was asked (conceptual, `multiSelect: true`):**
1. Proposed synthetic evaluators (multiSelect): Task Completion, RAG Faithfulness, Sentiment Analysis, Tool Usage Efficiency, None.
2. Plan approval.
3. Project name.
4. API key mode: Paste secret key (sk-kelet-...) / I'll grab one / I can't paste secrets here.

**Why:** Combines all remaining inputs (synthetics selection + plan confirmation + keys + project name + key-handling mode) into one batch per SKILL.md "No micro-confirmations between these". The three-option API key mode is required because synthetic evaluators were selected.

**Simulated user answer:**
- Synthetics: all four (Task Completion, RAG Faithfulness, Sentiment Analysis, Tool Usage Efficiency).
- Plan: approved.
- Project name: `docs-ai-iter8-sess`.
- Key mode: "Paste secret key", value `sk-kelet-eval-test`.

---

## Question slots NOT used

- **Slot 3** (deployment / secrets management): not needed — k8s with Helm charts + per-env overlays detected in repo; developer approved single-project mode in Q1; no ambiguity left.
- **PII question**: deliberately skipped per SKILL.md Sessions — phone is obvious PII, so `user_id=` is omitted and surfaced as a prominent warning instead of burning a question slot.
