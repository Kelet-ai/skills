# AskUserQuestion Calls

## Question 1 — Checkpoint 1: Architecture Confirmation

**Prompt:**
Does this diagram, map, and workflow summary accurately represent your system? Anything I missed?

**Context shown to developer:**
```
Use case: Documentation Q&A — answers developer questions about Kelet using BM25 search + page retrieval
Flows → Kelet projects:
  - "docs chat" → project "docs-ai-assistant"
User-facing: yes (plain HTML frontend, no React)
Stack: FastAPI + pydantic-ai (Bedrock Claude)
Config: .env (local) + K8s Secret (prod)
Deployment: Kubernetes via Helm (ArgoCD), AWS ALB ingress
Mode: full (developer explicitly requested)

Already wired:
  - kelet.configure() in app/main.py
  - kelet.agentic_session(session_id=...) in _run_agent_stream

Architecture:
  Browser (plain HTML)
       |
       | POST /chat {session_id, message, phone_number}
       v
  FastAPI (chat.py)
       |  session_id resolved from Redis
       |
       v
  kelet.agentic_session(session_id, user_id=phone_number)
       |
       v
  pydantic-ai chat_agent.iter()
       |
       |---> search_docs tool (BM25)
       |---> get_page tool (slug lookup)
       v
  SSE stream back to browser
  [X-Session-ID header exposed to browser]

Session semantics: UUID per conversation, stored in Redis (30 min TTL).
Phone number = stable user identity, passed as user_id= to Kelet.
```

**Simulated response:** "Yes, looks accurate."

---

## Question 2 — Checkpoint 2: Signal Plan + Evaluator Selection

**Prompt (multiSelect: true):**

Which synthetic evaluators should be activated for `docs-ai-assistant`?

Options:
- [x] Task Completion — Did the agent fully answer the developer question?
- [x] Sentiment Analysis — Did the user show frustration or repeated corrections?
- [x] Conversation Completeness — Were any user intentions left unaddressed?
- [x] Role Adherence — Did the agent stay within Kelet docs scope?
- [ ] RAG Faithfulness — Claims contradicting retrieved docs (requires retrieval context)
- [ ] Hallucination Detection — Fabricated facts
- [ ] None

Additional questions:
- Does the server-side signal plan look right? (tool errors + session abandonment)
- Confirm project name: `docs-ai-assistant` (already in .env and k8s prod.yaml)

**Simulated response:**
- Selected: Task Completion, Sentiment Analysis, Conversation Completeness, Role Adherence
- Plan approved
- Project name confirmed: docs-ai-assistant (already configured)

---

## Question 3 — Not Used

Developer explicitly opted for full mode, project name and API key already present in .env, no unknown deployment details. Third question slot was not needed.
