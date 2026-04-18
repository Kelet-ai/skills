# AskUserQuestion Log

Two AskUserQuestion calls total (within the skill's 2–3 budget).

## Q1 — Checkpoint 1: Mapping Confirmation

**Prompt:** "Does this diagram, map, and workflow summary accurately represent your system? Anything I missed? (Also: your session lives in Redis, server-generated UUID returned in `X-Session-ID`. Framework is pydantic-ai, which is auto-instrumented but does NOT know your session ID — I plan to wire `agentic_session(session_id=...)` around `chat_agent.iter(...)` so traces group correctly. Sound right?)"

**Options:**
- [selected] Yes, looks right. — proceed to signal analysis
- Something is off / I need to correct the map
- Session boundary is different from what you described

**Simulated developer answer:** "Yes, looks right."

**Rationale:** The developer confirmed the pydantic-ai + Redis-owned-session reading is accurate. Session boundary (Redis UUID per conversation, regenerated on new conversation) is already correct — no PII, so no `user_id=` concerns.

---

## Q2 — Checkpoint 2: Plan Approval + Synthetic Evaluator Selection + Keys

**Prompt (multiSelect + text inputs):**

1. **Pick synthetic evaluators for `docs-ai-eval`** (multiSelect):
   - [x] Task Completion — anchor, universally valuable
   - [x] Answer Relevancy — catches off-topic / padded / deflected answers
   - [x] RAG Faithfulness — catches claims contradicting the retrieved docs
   - [ ] Hallucination Detection — redundant with RAG Faithfulness for a retrieval agent
   - [ ] Sentiment Analysis — low value for a docs bot (low multi-turn emotion)
   - [ ] None

2. **Plan approval** — lightweight: `kelet.configure()` at startup + `agentic_session(session_id=...)` around both `/chat` handlers + synthetics auto-created via API. No frontend changes (plain HTML). No coded signals (no copy button / vote UI to wire to).

3. **Keys + project name:**
   - `KELET_API_KEY` = `sk-kelet-eval-test`
   - Project name = `docs-ai-eval`

4. **API key mode:**
   - [x] Paste secret key (sk-kelet-...) — primary auto-create
   - [ ] I'll grab one later
   - [ ] I can't paste secrets here (deeplink fallback)

**Simulated developer answers:**
- Evaluators: Task Completion, Answer Relevancy, RAG Faithfulness (3 proposed evaluators; the brief said "select all proposed").
- Plan: approve as-is.
- API key: `sk-kelet-eval-test` · project: `docs-ai-eval`.
- Key mode: "Paste secret key" (primary auto-create).

**Rationale:** Three evaluators cover Usefulness (Task Completion), Comprehension (Answer Relevancy), and Correctness (RAG Faithfulness) — one per failure category, no dimension duplication (per signals.md). `Hallucination Detection` dropped because the agent always retrieves — `RAG Faithfulness` subsumes it. Secret-paste mode is default/recommended and the only path that triggers real evaluator auto-create.

---

## Slot 3 (Unused)

Deployment was identified from context as Fly.io (not k8s-only), secrets pasted successfully — no third question needed.
