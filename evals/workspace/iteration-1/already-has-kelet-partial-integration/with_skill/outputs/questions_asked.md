# AskUserQuestion Calls

## Call 1 — Checkpoint 1: Mapping Confirmation

**Question:**
"Here's how I read your system:

```
Use case: Docs Q&A assistant — answers questions about your documentation
Stack: FastAPI + pydantic-ai (Python)
Session: server-generated UUID stored in Redis, returned as X-Session-ID header
Deployment: Docker + Kubernetes
Mode: lightweight (kelet already installed)
```

Data flow:
```
Browser → POST /chat → FastAPI
                         ├─ resolve/create Redis session (UUID)
                         └─ _run_agent_stream()
                              └─ chat_agent.iter() [pydantic-ai]
                                   ├─ search_docs() → BM25 retrieval
                                   └─ get_page() → full doc fetch
                                        └─ LLM (Bedrock/Claude)
```

The session ID is a UUID your app generates in Redis. That means the framework (pydantic-ai) doesn't see it — so `agentic_session(session_id=...)` is required to tell Kelet which traces belong together.

Does this accurately represent your system? Anything I missed?"

**Simulated developer answer:** "Yes, that's exactly right."

---

## Call 2 — Checkpoint 2: Confirm Plan + Collect Inputs

**Question (multiSelect: true):**
"I found two issues causing the missing sessions:

1. **Wrong method name** — `kelet.init()` doesn't exist in the SDK. The correct call is `kelet.configure()`.
2. **Missing `agentic_session()`** — without it, each LLM call appears as an unlinked trace. Fix: wrap `chat_agent.iter()` in `kelet.agentic_session(session_id=session.session_id)`.

**Proposed synthetic evaluators** (select which to activate):
- [ ] Task Completion — did the agent answer the user's question?
- [ ] RAG Faithfulness — did the answer stay faithful to retrieved docs?
- [ ] Answer Relevancy — did the answer address what was actually asked?
- [ ] None

**Plan approval:** Does the rest of the plan look right?

*(Your KELET_API_KEY and KELET_PROJECT are already in settings — no need to provide them again.)*"

**Simulated developer answer:** "Approve the plan. All three evaluators — Task Completion, RAG Faithfulness, Answer Relevancy."

---

## Total AskUserQuestion calls: 2 (within the 3-call budget, at the ideal 2)
