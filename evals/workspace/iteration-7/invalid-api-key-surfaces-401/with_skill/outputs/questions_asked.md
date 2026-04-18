# Questions Asked — Eval #8

Total `AskUserQuestion` calls: **2** (within the ≤3 budget, ideally 2).

Plus one **re-prompt** for the API key after the 401 rejection — this is NOT a new question
slot; it's a recovery on the same `KELET_API_KEY` input collected in Checkpoint 2.

---

### 1. Checkpoint 1 — mapping confirmation

**Q:** Does this diagram, project map, and workflow summary accurately represent your system?
Anything I missed?

**A:** confirmed.

---

### 2. Checkpoint 2 — plan approval + inputs (single multi-part `AskUserQuestion`)

**Q:**
- Which synthetic evaluators should I create? (multiSelect)
  - [x] Task Completion
  - [x] RAG Faithfulness
  - [x] Answer Relevancy
  - [ ] None
- Does the rest of the plan look right?
- Project name (create it at console.kelet.ai first):
- API key mode:
  - [x] Paste secret key (sk-kelet-…)
  - [ ] I'll grab one
  - [ ] I can't paste secrets here
- `KELET_API_KEY`:

**A:**
- Evaluators: all three selected
- Plan: approved
- Project: `docs-ai-401-eval`
- Key mode: Paste secret key
- Key: `sk-typo-wrong`  ← malformed, triggers 401

---

### Re-prompt (recovery, not a new slot)

After the curl returned `401 {"detail":"Not authenticated"}`, the skill surfaced the error and
re-asked **only for the key**:

> Your key was rejected by api.kelet.ai (401). Valid Kelet keys look like `sk-kelet-...`.
> Regenerate at https://console.kelet.ai/api-keys and paste here.

**A:** `sk-kelet-eval-test`  → curl re-run → **200 created=3 updated=0 failed=0**.

---

### Slot 3 (deployment)

**Not used.** Deployment was identified during silent analysis (k8s helm chart already present;
developer also mentioned Fly.io — env-var contract is identical). No need to burn slot 3.

---

## Behavioral notes (what the skill did NOT do)

- ✗ Did **not** silently fall back to the deeplink path on 401. Deeplink is reserved for
  "I can't paste secrets here" mode per SKILL.md.
- ✗ Did **not** treat the 401 as a generic network error or 5xx.
- ✗ Did **not** ask a fresh `AskUserQuestion` for the whole Checkpoint 2 again — only
  re-requested the single failed input (the key).
- ✓ Recognized `sk-typo-wrong` as clearly not matching `sk-kelet-*` prefix and flagged likely
  paste error in the re-prompt.
