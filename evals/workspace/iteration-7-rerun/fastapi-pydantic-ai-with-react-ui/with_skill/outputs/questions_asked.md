# Questions Asked

Budget: at most 3 `AskUserQuestion` calls (ideally 2). Used: **2**.

---

## Q1 — Checkpoint 1: Mapping confirmation

**Question:** Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?

**Options:**

- Yes — proceed
- Correct session mapping (details below)
- Correct project/flow split (details below)
- Other (details below)

**Developer answer:** Yes — proceed.

---

## Q2 — Checkpoint 2: Plan approval + inputs + key mode

**Multi-part `AskUserQuestion` (multiSelect: true):**

1. **Proposed synthetic evaluators** (pick which go into the project):
   - Task Completion
   - RAG Faithfulness
   - Answer Relevancy
   - None

2. **Plan approval:** Does the rest of the plan look right? (`kelet.configure()`, `agentic_session(session_id=...)` around both agent call-sites, scaffold React + `KeletProvider`, `VoteFeedback` on AI bubbles wired to `X-Session-ID`)

3. **Keys + project name:**
   - `KELET_API_KEY` (secret, `sk-kelet-...`) — required for synthetic auto-create
   - `VITE_KELET_PUBLISHABLE_KEY` (`pk-kelet-...`) — for VoteFeedback
   - Project name

4. **API key mode:**
   - Paste secret key (`sk-kelet-...`)
   - I'll grab one
   - I can't paste secrets here

**Developer answers:**
- Evaluators: all three (Task Completion, RAG Faithfulness, Answer Relevancy).
- Plan approved.
- `KELET_API_KEY=sk-kelet-eval-test`, `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test`, project `docs-ai-react-eval`.
- Key mode: Paste secret key.
- Scaffold React: yes.

---

## Q3 — (not used)

Deployment was identified at analysis time (Fly.io + Vercel, with a K8s Helm chart also present) and secrets were handled directly via env vars, so question slot 3 was not needed.
