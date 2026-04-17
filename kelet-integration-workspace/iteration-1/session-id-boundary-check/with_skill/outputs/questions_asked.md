# AskUserQuestion Calls

## Question 1 — Checkpoint 1: Mapping Confirmation

**Presented to developer:**

---

🔍  ANALYSIS · PROJECT + WORKFLOW MAPPING

```
Use case: Documentation Q&A assistant — multi-turn chat helping users find
          answers in product docs (currently Kelet docs). Users can start
          fresh conversations at any time.

Flows → Kelet projects:
  - "docs Q&A chat" → project "docs-ai-assistant"

User-facing: yes (embedded chat widget, API consumed by frontend clients)
Stack: FastAPI + pydantic-ai (Python) — server-side only, no React frontend
Config: .env (local), K8s ConfigMap + Secret (production via Helm)
Deployment: Kubernetes / Helm (k8s/charts/docs-ai) + GitHub Actions CI
Mode: lightweight
```

**Architecture diagram:**

```
Client (browser / phone app)
    │  POST /chat  { message, session_id?, phone_number? }
    ▼
FastAPI  ──  rate_limiter (Redis, per-IP)
    │
    ├── get_session(redis, session_id)  ←── UUID stored in Redis (TTL 30 min)
    │   └── create_session() if missing/expired → new UUID
    │
    ├── chat_agent.iter(message, deps, history)   [pydantic-ai]
    │       └── tools: search_docs / get_page (BM25 + full page fetch)
    │
    └── StreamingResponse (SSE)
            headers: X-Session-ID: <uuid>
```

⚠️ **Session identity note:** You mentioned phone number is the only user identifier and there's no per-conversation UUID. However, the app already generates a UUID per conversation (`create_session()` in `src/cache/__init__.py`) — this UUID is stored in Redis and returned to the client as `X-Session-ID`. The phone number lives at the client level and isn't currently sent to the server.

**For Kelet:** The UUID is the correct session boundary (it changes on new conversation). Phone number should be passed as `user_id` so Kelet can correlate sessions across conversations for the same user. The fix: add an optional `phone_number` field to `ChatRequest`; the app already generates the right UUID — no UUID generation needed.

**Question asked (AskUserQuestion):**
> "Does this diagram, map, and workflow summary accurately represent your system? One note on sessions: your app already generates a UUID per conversation — I'd add an optional `phone_number` field to `ChatRequest` so clients can pass it through to Kelet as `user_id` (for cross-session user correlation). Does that match what you want? Anything else I missed?"

**Developer response:** Confirmed correct. Approved adding phone_number as optional user_id field.

---

## Question 2 — Checkpoint 2: Confirm Plan + Collect Inputs

**Presented to developer:**

---

📍  Analysis ✅ → Signal Analysis ✅ → Checkpoint 2 🔄

**Signal findings:**
- pydantic-ai is auto-instrumented by Kelet — traces captured automatically once `kelet.configure()` is called
- `agentic_session()` IS required: the app owns the session ID (Redis UUID), not the framework — without it, sessions appear as unlinked traces in Kelet
- No React frontend — VoteFeedback not applicable; no publishable key needed
- No existing feedback hooks found — keeping lightweight (0 coded signals)

**Proposed plan:**
1. `kelet.configure()` at startup in `app/main.py` — captures all pydantic-ai traces
2. `kelet.agentic_session(session_id=session.session_id, user_id=phone_number)` wrapping agent runs in `src/routers/chat.py`
3. Add `phone_number: str | None = None` to `ChatRequest` — passed as `user_id` to Kelet for cross-session correlation
4. Add `KELET_API_KEY` + `KELET_PROJECT` to `.env`
5. K8s deployment: `KELET_PROJECT` already in ConfigMap, `KELET_API_KEY` already wired via K8s Secret (`docs-ai-kelet`) — no Helm changes needed

**Synthetic evaluator proposals (multiSelect):**
- [x] **Task Completion** — Did the agent successfully answer the user's documentation question?
- [ ] Conversation Completeness — user intentions left unaddressed
- [ ] Answer Relevancy — off-topic or padded responses
- [ ] None

**Question asked (AskUserQuestion, multiSelect: true):**
> 1. Which synthetic evaluators do you want activated? (select all that apply)
>    - Task Completion ← recommended
>    - Conversation Completeness
>    - Answer Relevancy
>    - None
> 2. Does the rest of the plan look right?
> 3. Confirm your project name (create first at console.kelet.ai → top-nav → New Project): **docs-ai-assistant**
> 4. Paste your `KELET_API_KEY` (get at console.kelet.ai/api-keys):

**Developer responses:**
- Evaluators selected: Task Completion
- Plan approved: yes
- Project name: docs-ai-assistant
- KELET_API_KEY: sk-kelet-test-123

**Deeplink generated:**
`https://console.kelet.ai/docs-ai-assistant/synthetics/setup?deeplink=eyJ1c2VfY2FzZSI6IkRvY3VtZW50YXRpb24gUSZBIGFzc2lzdGFudCBcdTIwMTQgbXVsdGktdHVybiBjaGF0IGhlbHBpbmcgdXNlcnMgZmluZCBpbmZvcm1hdGlvbiBpbiBwcm9kdWN0IGRvY3MuIFVzZXJzIGNhbiBzdGFydCBmcmVzaCBjb252ZXJzYXRpb25zLiIsImlkZWFzIjpbeyJuYW1lIjoiVGFzayBDb21wbGV0aW9uIiwiZXZhbHVhdG9yX3R5cGUiOiJsbG0iLCJkZXNjcmlwdGlvbiI6IkRpZCB0aGUgYWdlbnQgc3VjY2Vzc2Z1bGx5IGFuc3dlciB0aGUgdXNlciBxdWVzdGlvbiBhYm91dCB0aGUgZG9jdW1lbnRhdGlvbj8ifV19`

**Total AskUserQuestion calls: 2** (within the 3-max budget, achieving the ideal 2)
