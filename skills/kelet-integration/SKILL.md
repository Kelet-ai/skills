---
name: kelet-integration
description: Use when integrating Kelet into an AI application — setting up tracing, user feedback collection, and session correlation across Python, TypeScript/Node.js, Next.js, and React frontends. Triggers on requests to "add Kelet", "instrument my agent", "set up Kelet tracing", "add feedback collection", or "integrate with Kelet".
license: CC-BY-4.0
metadata:
  author: kelet-ai
  url: https://kelet.ai
  version: "1.0.1"
---

# Kelet Integration

Kelet is an AI agent that does Root Cause Analysis for AI app failures. It ingests traces + user signals → clusters failure patterns → generates hypotheses → suggests fixes. This skill integrates Kelet into a developer's AI application end-to-end.

**Kelet never crashes your app.** All SDK errors — misconfigured keys, network failures, wrong session IDs, missing extras — are swallowed silently to ensure QoS. A misconfigured integration looks identical to a working one. The Common Mistakes section documents every known silent failure mode.

**Always follow phases in order: 0a → 0b → 0c → 0d → 1 → implement.**

---

## Phase 0a: Project Mapping (ALWAYS first)

Infer from existing files (README, CLAUDE.md, entrypoints, dependency files, `.env`) before asking. Only ask what you can't determine.

**Questions to resolve (ask only if unclear after reading files):**

1. What is the agentic use case?
2. How many distinct agentic flows? → maps to Kelet project count
   > A flow is isolated and standalone with clear ownership boundaries. If flow A triggers flow B with a clear interface boundary = TWO projects. Same flow in prod vs staging = TWO projects.
3. Is this user-facing? (determines whether React/VoteFeedback applies)
4. Stack: server (Python/Node.js/Next.js) + LLM framework + React?
5. Config pattern: `.env` / `.envrc` / YAML / K8s secrets?
   > Writing keys to the wrong file is a silent failure — Kelet appears uninstrumented with no error.

**Produce a Project Map before proceeding:**
```
Use case: [what the agents do]
Flows → Kelet projects:
  - flow "X" → project "X"
  - flow "Y" → project "Y"
User-facing: yes/no
Stack: [server framework] + [LLM framework]
Config: .env / .envrc / k8s
```

---

## Phase 0b: Agentic Workflow + UX Mapping

The purpose of this phase is to map what "failure" looks like for Kelet's RCA engine — Kelet clusters spans by failure pattern, so you need to understand failure modes before proposing signals.

**Workflow** (what the agent does):
- Steps and decision points
- Where it could go wrong: wrong retrieval, hallucination, off-topic, loops, timeouts
- What success vs. failure looks like from the agent's perspective

**UX** (if user-facing):
- What AI-generated content is shown? (answers, suggestions, code, summaries)
- Where do users react? (edit it, retry, copy, ignore, complain)
- What implicit behaviors signal dissatisfaction? (abandon, rephrase, undo)

Outputs from this phase feed directly into signal selection in 0c — each identified failure mode becomes a signal candidate.

---

## Phase 0c: Signal Brainstorming

Reason about failure modes, then propose specific signals — not a generic list.

Kelet clusters failure patterns across sessions — noisy or redundant signals dilute clustering quality. **Propose 3–5 signals per flow** (cap at 5, prioritized by specificity to the failure mode). For each: what it captures, how it manifests, what failure it reveals to Kelet's RCA engine.

**Synthetic signals: generate a deeplink, not code.**
After confirming coded signal selection with the developer, generate a deeplink for the platform's AI evaluator wizard:
1. Compose `use_case` from Phase 0b (2–4 sentences: what the agent does, key failure modes, user interactions)
2. Generate 3–5 ideas matching identified failure modes:
   - `evaluator_type: "llm"` for semantic checks (hallucination, task completion, relevancy, role adherence)
   - `evaluator_type: "code"` for structural checks (loop detection, tool failure rate, latency thresholds)
   - Add `context` only when you have specific steering text for that evaluator
3. Base64url-encode the payload: `btoa(JSON.stringify({use_case, ideas})).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'')`
4. Present to the developer:
   > Click this link to set up AI-powered evaluators tailored to your agent:
   > `https://console.kelet.ai/synthetics/setup?deeplink=<encoded>`
   >
   > This will generate evaluators for: [list idea names]. Click "Activate All" once you've reviewed them.

Only write `source=SYNTHETIC` signal code if the developer explicitly asks AND the platform cannot implement it (explain why + ask to confirm).

**Multi-select ask:**
> "Here are the most valuable signals for your workflow. Select what to implement:"
>
> Tracing (always included): [ ] flow X  [ ] flow Y
> Explicit feedback: [ ] VoteFeedback at [location] — "was this helpful?"
> Implicit feedback: [ ] Edit tracking on [editable output] — "user corrected this"
> Automated: [ ] Signal when [condition] — e.g., tool call fails, output rejected
>
> Platform synthetics (deeplink generated after this step): [ ] LLM-as-judge for [quality concern]

See [references/signals.md](references/signals.md) for signal kinds, sources, and when to use each.

---

## Phase 0d: What You'll See in Kelet

| After implementing | Visible in Kelet console |
|---|---|
| `kelet.configure()` | LLM spans in Traces: model, tokens, latency, errors |
| `agentic_session()` | Sessions view: full conversation grouped for RCA |
| VoteFeedback | Signals: 👍/👎 correlated to the exact trace that generated the response |
| Edit signals (`useFeedbackState`) | Signals: what users corrected — reveals model errors |
| Platform synthetics | Signals: automated quality scores Kelet runs on your behalf |

---

## Sessions

A session is the logical boundary of one unit of work — all LLM calls, tool uses, agent hops, and retrievals that belong to the same context. Not tied to conversations: a batch processing job, a scheduled pipeline, or a chat thread are all valid sessions. New context = new session.

**The framework orchestrates the flow** (pydantic-ai runs your agent loop, LangGraph manages your graph execution, a LangChain chain runs end-to-end): Kelet infers sessions automatically — no `agentic_session()` needed. Supported frameworks: pydantic-ai, LangChain/LangGraph, LlamaIndex, CrewAI, Haystack, DSPy, LiteLLM, Langfuse, and any framework using OpenInference or OpenLLMetry instrumentation. If the framework isn't listed, research whether it uses one of these instrumentation libraries before omitting `agentic_session()`.

Note: **Vercel AI SDK does not set session IDs automatically** — use `agenticSession()` at the route level (see Next.js section).

**You own the loop** (you write the code that calls agent A, passes results to agent B, chains steps in Temporal, a custom loop, or any orchestrator you built — even if individual steps use a supported framework internally): the framework doesn't set a session ID for the overall flow. You MUST use `agentic_session(session_id=...)` / `agenticSession({ sessionId }, callback)`. (**Silent if omitted — spans appear as unlinked individual traces.**)

---

## Phase 1: API Key Setup

Two key types — never mix them:
- **Secret key** (`KELET_API_KEY`): server-only. Traces LLM calls. Never expose to frontend.
- **Publishable key** (`VITE_KELET_PUBLISHABLE_KEY` / `NEXT_PUBLIC_KELET_PUBLISHABLE_KEY`): frontend-safe. Used in `KeletProvider` for VoteFeedback widget.

Ask the developer for keys, then write to the correct file based on the detected config pattern:
- `.env` → `KEY=value`
- `.envrc` (direnv) → `export KEY=value`
- K8s → tell developer to add to secrets manifest

Add both vars to `.gitignore` if not already present.

---

## Implementation: Key Concepts by Stack

See [references/api.md](references/api.md) for exact function names, package names, and the one TS gotcha.

**Python**: `kelet.configure()` at startup auto-instruments pydantic-ai/Anthropic/OpenAI/LangChain. Each LLM framework extra must be installed (`kelet[anthropic]`, `kelet[openai]`, etc.) — if missing, `configure()` silently skips that library. `agentic_session()` is **required whenever you own the orchestration loop**. If a supported framework orchestrates for you, sessions are inferred automatically — no wrapper needed. See Sessions section above. `kelet.agent(name=...)` — use when: (a) multiple agents run in one session and need separate attribution, or (b) your framework doesn't expose agent names natively (pydantic-ai does; OpenAI/Anthropic/raw SDKs don't — Kelet can't infer it). Logfire users: `kelet.configure()` detects the existing `TracerProvider` — no conflict.

Streaming: wrap the **entire** generator body (not the caller), including the final sentinel — trailing spans are silently lost otherwise:
```python
async def stream_response():
    async with kelet.agentic_session(session_id=...):
        async for chunk in llm.stream(...):  # sentinel included in scope
            yield chunk
```

**TypeScript/Node.js**: `agenticSession` is **callback-based** (not a context manager). AsyncLocalStorage context propagates through the callback's call tree — there's no `with`-equivalent in Node.js, so the callback IS the scope boundary. Node.js only (not browser-compatible). Also requires OTEL peer deps alongside `kelet` — see Implementation Steps.

**Next.js**: `KeletExporter` in `instrumentation.ts` via `@vercel/otel`. Two required steps often missed: (1) `experimental: { instrumentationHook: true }` in `next.config.js` — without it, `instrumentation.ts` never runs (**Silent**); (2) each Vercel AI SDK call needs `experimental_telemetry: { isEnabled: true }` — telemetry is off by default (**Silent**).

**Multi-project apps**: Call `configure()` once with no project. Override per call with `agentic_session(project=...)`. W3C Baggage propagates the project to downstream microservices automatically.

**React**: `KeletProvider` at app root sets `apiKey` + default project. For multiple AI features belonging to different Kelet projects: nest a second `KeletProvider` with only `project=` — it inherits `apiKey` from the outer provider. No need to repeat the key.

**VoteFeedback**: `session_id` passed to `VoteFeedback.Root` must exactly match what the server used in `agentic_session()`. If they differ, feedback is captured but silently unlinked from the trace.

**Session ID propagation** (how feedback links to traces):
Client generates UUID → sends in request body → server uses in `agentic_session(session_id=...)` → server returns it as `X-Session-ID` response header → client passes it to `VoteFeedback.Root`. (**Silent if mismatched — no error, feedback captured but unlinked from the trace.**)

**Implicit feedback — three patterns, each for a different use case:**
- **`useFeedbackState`**: drop-in for `useState`. Each `setState` call accepts a trigger name as second arg — tag AI-generated updates `"ai_generation"` and user edits `"manual_refinement"`. Without trigger names, all state changes look identical and Kelet can't distinguish "user accepted AI output" from "user corrected it."
- **`useFeedbackReducer`**: drop-in for `useReducer`. Action `type` fields automatically become trigger names — zero extra instrumentation for reducer-based state.

**Which to use:** Explicit rating of AI response → `VoteFeedback`. Editable AI output → `useFeedbackState` with trigger names. Complex state with action types → `useFeedbackReducer`.

---

## Decision Tree

```
N agentic flows?
├─► 1  ──► configure(project="name") at startup
└─► N  ──► configure() once, agentic_session(project=...) per flow

Stack?
├─► Python   ──► kelet.configure() + agentic_session() context manager
├─► Node.js  ──► configure() + agenticSession({sessionId}, callback)
└─► Next.js  ──► instrumentation.ts + KeletExporter

User-facing with React?
├─► Yes ──► KeletProvider at root
│           ├─► Multiple flows? → nested KeletProvider per flow (project only)
│           └─► VoteFeedback at AI response sites + session propagation
└─► No  ──► Server-side only

Feedback signals?
├─► Explicit (votes)     ──► VoteFeedback / kelet.signal(kind=FEEDBACK, source=HUMAN)
├─► Implicit (edits)     ──► useFeedbackState (tag AI vs human updates with trigger names)
├─► Reducer-based state  ──► useFeedbackReducer (action.type = trigger name automatically)
└─► Automated metrics    ──► Generate deeplink → console.kelet.ai/synthetics/setup
```

---

## Implementation Steps

1. **Project Map** — infer from files, confirm flow → project mapping
2. **API keys** — ask for keys, detect config pattern, write to correct file
3. **Install** — Python: `kelet[all]` or per-library extras. Node.js/Next.js: `kelet` + OTEL peer deps (`@opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-http`) — Python needs no OTEL deps. React: `@kelet-ai/feedback-ui`
4. **Instrument server** — `configure()` at startup + `agentic_session()` per flow
5. **Instrument frontend** — `KeletProvider` at root, nested per flow if multi-project
6. **Connect feedback** — VoteFeedback + session ID propagation if user-facing
7. **Verify** — type check, confirm env vars set, open Kelet console and confirm traces appear

---

## Common Mistakes

| Mistake | Symptom | Notes |
|---|---|---|
| Secret key in `KeletProvider` / frontend env | Key leaked in JS bundle | Use publishable key in frontend. **Silent until key is revoked.** |
| Keys written to wrong config file (`.env` vs `.envrc`) | App starts but no traces appear | Check config pattern before writing. **Silent failure.** |
| `agentic_session` exits before streaming generator finishes | Traces appear incomplete | Wrap entire generator body including `[DONE]` sentinel. **Silent.** |
| VoteFeedback `session_id` doesn't match server session | Feedback unlinked from traces | Capture `X-Session-ID` header; use exact same value. **Silent.** |
| `configure(project=...)` on a multi-project app | All sessions attributed to one project | Use `configure()` with no project; override in `agentic_session()`. |
| No `kelet.agent(name=...)` with OpenAI/Anthropic/AI SDK | Kelet shows unattributed spans — RCA can't identify which agent failed | pydantic-ai exposes names natively (auto-inferred); raw SDKs don't. **Silent.** |
| Python extra not installed (e.g. missing `kelet[anthropic]`) | `configure()` succeeds, zero traces from that library | Install the matching extra — Kelet silently skips uninstrumented libraries. **Silent.** |
| Node.js: `npm install kelet` only, missing OTEL peer deps | Import errors or no traces | Add `@opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-http`. Python needs no peer deps. |
| Next.js: missing `instrumentationHook: true` in `next.config.js` | `instrumentation.ts` exists but never runs, zero traces | Add `experimental: { instrumentationHook: true }` to `next.config.js`. **Silent.** |
| Vercel AI SDK: missing `experimental_telemetry: { isEnabled: true }` per call | `configure()` succeeds, zero traces from AI SDK calls | Vercel AI SDK telemetry is off by default. Must opt in per call. **Silent.** |
| DIY orchestration without `agentic_session()` | Sessions appear fragmented — each LLM call is a separate unlinked trace in Kelet | Required whenever you own the loop: Temporal, manual agent chaining, custom orchestrators, raw SDK calls. **Silent.** |
