# Questions asked (simulated)

Total `AskUserQuestion` slots used: 2 (budget allows up to 3, ideal 2). No pre-flight needed — app context was provided in trigger.

## Checkpoint 1 — Mapping confirmation

**Question:** "Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?"

**Presented:**
- ASCII diagram: React (Vite) → POST /chat (SSE) → FastAPI → pydantic-ai Agent → Bedrock Claude; session UUID generated server-side, returned in `X-Session-ID`, held in React `useRef`, echoed back on follow-ups, reused as `kelet_session_id`.
- Project map:
  - Use case: docs Q&A chatbot (RAG over llms.txt, BM25 search).
  - Flow → project: single flow → `docs-ai-react-eval`.
  - User-facing: yes. Stack: FastAPI + pydantic-ai (auto-instrumented), React 18 + Vite.
  - Config: `.env` (server) + `frontend/.env` (Vite). Deploy: Vercel (frontend) + Fly.io (backend); k8s chart already present for prod.
  - Mode: full (React UI + VoteFeedback + synthetics).
- Session semantics: server-generated UUID per conversation, regenerated at session expiry → **correct** (no stable-user-identity mismatch, no PII).
- React frontend does not exist on this branch — proposed scaffolding a minimal Vite + TS + React 18 chat UI under `frontend/` and wiring VoteFeedback into it.

**Developer answer:** Confirmed mapping. Approved scaffolding a new React frontend under `frontend/`.

## Checkpoint 2 — Confirm plan + collect inputs + pick evaluators

**Question (multiSelect):** "Pick the synthetic evaluators to provision, confirm the plan, and share keys + project + key mode."

**Proposed synthetic evaluators (one per failure category — no overlap):**
1. `Task Completion` (llm) — Usefulness. Did we actually answer the docs question?
2. `Answer Relevancy` (llm) — Comprehension. On-topic, no drift.
3. `RAG Faithfulness` (llm) — Correctness, grounded to retrieved pages (BM25 search_docs / get_page tool calls).
4. None.

**Developer answers:**
- Evaluators: selected 1, 2, 3 (all proposed).
- Plan approved.
- `KELET_API_KEY=sk-kelet-eval-test`
- `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-eval-test`
- Project: `docs-ai-react-eval`
- Key mode: **Paste secret key** → primary API auto-create.

No third question used. Deployment (Vercel + Fly.io + existing k8s chart) was visible in-repo, so slot 3 was not needed.
