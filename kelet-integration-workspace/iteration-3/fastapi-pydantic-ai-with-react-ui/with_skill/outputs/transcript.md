# Integration Transcript — Kelet Integration Skill Execution

**App:** FastAPI + pydantic-ai backend, React/Vite frontend, plain chat UI  
**Task:** "integrate kelet into my app"

---

## Welcome

Welcome! I'm going to integrate Kelet into your docs-ai app. Before any code, a quick orientation:

- **Trace** — automatic recording of one LLM call: model, inputs, outputs, latency, tokens, errors. `kelet.configure()` captures these with zero code changes.
- **Session** — a group of traces belonging to one conversation. Sessions are how Kelet correlates multi-turn LLM calls.
- **Signal** — a tip at a meaningful moment: thumbs-down = "start looking here". Edits and votes narrow the investigation.
- **Synthetic** — an automated evaluator Kelet runs on every session using trace data it already has. Zero developer code.
- **Project** — a logical boundary for one use case. Wrong project = silent routing failure, data goes nowhere.

Silent analysis first, then at most 2 questions.

---

## 🔍  ANALYSIS · PROJECT + WORKFLOW MAPPING

**Reading:** pyproject.toml, app/main.py, src/routers/chat.py, frontend/src/App.tsx, frontend/src/main.tsx, frontend/src/App.module.css, frontend/package.json, .env, k8s/charts/docs-ai/templates/

**Findings:**

- **Deps:** `kelet>=1.3.0` in pyproject.toml. pydantic-ai (supported framework). `@kelet-ai/feedback-ui` in frontend package.json.
- **Backend entrypoint:** `app/main.py` — `kelet.configure()` already called at module level. Reads `KELET_API_KEY` + `KELET_PROJECT` from env.
- **LLM call sites:** `src/routers/chat.py` — `_run_agent_stream()` wraps `chat_agent.iter()` in `kelet.agentic_session(session_id=session.session_id)`. Complete: session context spans the entire streaming generator including `[DONE]`.
- **Session tracking:** Server-generated UUID (`create_session()` → Redis). Returned in `X-Session-ID` response header. CORS exposes header. React stores in `useState`. Session ID changes when `session_id` is absent or expired → correct boundary.
- **Existing feedback UI:** None. No thumbs, ratings, copy, retry, or edit buttons in the baseline App.tsx.
- **Deployment:** App description: Vercel (frontend) + Fly.io (backend). Infra scan found `k8s/` with Helm charts (production deployment). `KELET_API_KEY` in k8s Deployment via `secretKeyRef` (secret name from values). `KELET_PROJECT` in ConfigMap. Keys already in `.env` for local dev.
- **Config pattern:** `.env` file. `KELET_API_KEY=sk-kelet-test-123`, `KELET_PROJECT=docs-ai-assistant`, `VITE_KELET_PUBLISHABLE_KEY=pk-kelet-test-456`, `VITE_KELET_PROJECT=docs-ai-assistant` — all present.

**Project Map:**
```
Use case: Documentation AI assistant — answers questions using docs knowledge base
Flows → Kelet projects:
  - chat flow → project "docs-ai-assistant"
User-facing: yes (React Vite)
Stack: FastAPI + pydantic-ai / React Vite
Config: .env (already populated)
Deployment: Vercel (frontend) + Fly.io (backend) per description; k8s/Helm found in repo
Mode: lightweight (backend already instrumented)
```

**Architecture:**
```
React (Vite)
  KeletProvider (pk-kelet-...)    ← needs adding
       |
  VoteFeedback.Root(session_id)   ← needs adding on assistant messages
       |
  POST /api/chat  ←→  FastAPI
                          |
                   kelet.configure()  ✅ already
                          |
                   agentic_session(session_id)  ✅ already
                          |
                   pydantic-ai agent  →  LLM
                          |
                   X-Session-ID header  ✅ returned
```

---

## Checkpoint 1 — AskUserQuestion

> Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?

**[Simulated answer: Yes, accurate.]**

📍  Analysis ✅ → Checkpoint 1 ✅ → Signal Analysis 🔄 → Checkpoint 2 ○ → impl ○

---

## Signal Analysis Pass (Silent)

**Coded signals scan:**
- No copy button, no retry, no edit-in-place, no session reset button
- No existing event handlers to wire signals to beyond the Send button
- VoteFeedback is the only viable coded signal — adds thumbs up/down to each assistant message

**Synthetic evaluator selection (for this agent):**
- Task Completion — did the assistant answer the docs question? Always applicable.
- Sentiment Analysis — detects user frustration/repeated corrections in multi-turn chat. Applicable for any user-facing assistant.
- Answer Relevancy — overlaps with Task Completion for this use case → skip (same failure category)
- Conversation Completeness — overlaps with Task Completion → skip
- RAG Faithfulness — no retrieval context exposed in traces → not applicable

**Proposed evaluators:** Task Completion + Sentiment Analysis

---

## Checkpoint 2 — AskUserQuestion (with multiSelect)

**Proposed plan (lightweight):**

Backend — already complete:
- `kelet.configure()` at startup ✅
- `kelet.agentic_session(session_id=session.session_id)` wrapping agent stream ✅

Frontend — to add:
1. `KeletProvider` in `main.tsx` wrapping App (publishable key)
2. `VoteFeedback` compound component on each assistant message in `App.tsx`

Synthetics — no code:
- Task Completion + Sentiment Analysis via deeplink

**Select synthetic evaluators:**
- [x] Task Completion
- [x] Sentiment Analysis
- [ ] Conversation Completeness
- [ ] Answer Relevancy
- [ ] None

**Plan approval:** approve

**Keys + project:**
- `KELET_API_KEY`: already in `.env` ✓
- `VITE_KELET_PUBLISHABLE_KEY`: already in `.env` ✓
- Project name: `docs-ai-assistant` (confirmed)

**[Simulated answer: Task Completion + Sentiment Analysis selected. Plan approved. project="docs-ai-assistant", keys confirmed.]**

---

## Deeplink Generation (Bash execution)

```
python3 -c "import base64,json; project='docs-ai-assistant'; payload={...}; print(...)"
```

**Deeplink URL:**
**https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gQUkgYXNzaXN0YW50IFx1MjAxNCBhbnN3ZXJzIHVzZXIgcXVlc3Rpb25zIGJ5IHNlYXJjaGluZyBhbmQgcmV0cmlldmluZyByZWxldmFudCBkb2NzLiBQbGFpbiBjaGF0IGludGVyZmFjZSwgbXVsdGktdHVybiBjb252ZXJzYXRpb24uIiwiaWRlYXMiOlt7Im5hbWUiOiJUYXNrIENvbXBsZXRpb24iLCJldmFsdWF0b3JfdHlwZSI6ImxsbSIsImRlc2NyaXB0aW9uIjoiRGlkIHRoZSBhc3Npc3RhbnQgc3VjY2Vzc2Z1bGx5IGFuc3dlciB0aGUgdXNlciBxdWVzdGlvbiB1c2luZyB0aGUgYXZhaWxhYmxlIGRvY3VtZW50YXRpb24_In0seyJuYW1lIjoiU2VudGltZW50IEFuYWx5c2lzIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRldGVjdCB1c2VyIGZydXN0cmF0aW9uLCByZXBlYXRlZCBjb3JyZWN0aW9ucywgb3IgZGlzc2F0aXNmYWN0aW9uIHRocm91Z2hvdXQgdGhlIGNvbnZlcnNhdGlvbiBzZXNzaW9uLiJ9XX0**

---

## What you'll see

| After implementing | Visible in Kelet console |
|---|---|
| `kelet.configure()` | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()` | Sessions view: full conversation grouped for RCA |
| VoteFeedback | Signals: thumbs up/down correlated to exact trace |
| Platform synthetics | Signals: automated Task Completion + Sentiment scores |

---

## Implementation

📍  Analysis ✅ → Checkpoint 1 ✅ → Signal Analysis ✅ → Checkpoint 2 ✅ → impl 🔄

### Plan (entered /plan mode)

1. `frontend/src/main.tsx` — add `KeletProvider` wrapping `<App />` with publishable key + project from Vite env vars
2. `frontend/src/App.tsx` — extract `AssistantMessage` component, add `VoteFeedback.Root/UpvoteButton/DownvoteButton/Popover` styled with `styles.iconBtn`
3. `frontend/src/App.module.css` — already has `.iconBtn` class; verify no overflow:hidden on assistant message container
4. Backend — no changes needed (already instrumented)
5. `.env` — already populated, no changes
6. Production secrets — Fly.io: `fly secrets set KELET_API_KEY=<value>`; Vercel: Dashboard → Settings → Environment Variables → add `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`

### Execution

**frontend/src/main.tsx** — added `KeletProvider` with `VITE_KELET_PUBLISHABLE_KEY` + `VITE_KELET_PROJECT`

**frontend/src/App.tsx** — added `VoteFeedback` compound component:
- `VoteFeedback.Root session_id={sessionId}` — exact value from `X-Session-ID` header state
- `VoteFeedback.UpvoteButton asChild` + `<button className={styles.iconBtn}>` — uses app's existing icon button style
- `VoteFeedback.DownvoteButton asChild` + `<button className={styles.iconBtn}>` — same
- `VoteFeedback.Popover` positioned `absolute` / `bottom: calc(100% + 8px)` — dark-theme inline styles matching app palette
- `VoteFeedback.SubmitButton className={styles.sendBtn}` — matches the main Send button

---

## Phase V: Verification Checklist

- [x] `kelet.configure()` called once at startup (app/main.py module level)
- [x] `agentic_session()` wraps entire streaming generator including `[DONE]` sentinel
- [x] Session ID consistent end-to-end: `create_session()` → `X-Session-ID` header → React `sessionId` state → `VoteFeedback.Root session_id`
- [x] Secret key (`KELET_API_KEY`) server-only; publishable key (`VITE_KELET_PUBLISHABLE_KEY`) in KeletProvider
- [x] No `<button>` inside `<button>`: used `asChild` prop on VoteFeedback vote buttons
- [x] `VoteFeedback.Popover` has `position: absolute` on popover + `position: relative` wrapper — no overflow:hidden on `.assistantMessage`
- [x] pydantic-ai supported framework — sessions auto-inferred but agentic_session() required because app owns session_id
- [ ] Smoke test: trigger chat → open console.kelet.ai/docs-ai-assistant → verify traces appear (developer action)
- [ ] Production secrets: `fly secrets set KELET_API_KEY=sk-kelet-... KELET_PROJECT=docs-ai-assistant` on Fly.io; Vercel env vars for frontend keys

**Production deployment note:**  
`.env` is local dev only. For production:
- **Fly.io (backend):** `fly secrets set KELET_API_KEY=<value> KELET_PROJECT=docs-ai-assistant`
- **Vercel (frontend):** Dashboard → project → Settings → Environment Variables → add `VITE_KELET_PUBLISHABLE_KEY` and `VITE_KELET_PROJECT`
- **k8s (Helm):** `KELET_API_KEY` already wired to k8s Secret via `secretKeyRef` in deployment template; `KELET_PROJECT` in ConfigMap — ensure secret exists in the cluster.
