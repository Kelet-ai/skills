---
name: kelet-integration
description: >
  Integrates Kelet into AI applications end-to-end: instruments agentic flows with OTEL tracing, maps session
  boundaries, adds user feedback signals (VoteFeedback, edit tracking, coded behavioral hooks), generates
  synthetic evaluator deeplinks, and verifies the integration. Kelet is an AI agent that performs Root Cause
  Analysis on AI app failures — it ingests traces and signals, clusters failure patterns, and suggests fixes.
  Use when the developer mentions Kelet or asks to integrate, set up, instrument, or add tracing/signals/feedback
  to their AI app. Triggers on: "integrate Kelet", "set up Kelet", "add Kelet", "instrument my agent",
  "connect Kelet", "use Kelet".
license: CC-BY-4.0
metadata:
  author: kelet-ai
  url: https://kelet.ai
  version: "1.3.0"
---

# Kelet Integration

Kelet is an AI agent that does Root Cause Analysis for AI app failures. It ingests traces + user signals → clusters failure patterns → generates hypotheses → suggests fixes. This skill integrates Kelet into a developer's AI application end-to-end.

**Kelet never crashes your app.** All SDK errors — misconfigured keys, network failures, wrong session IDs, missing extras — are swallowed silently to ensure QoS. A misconfigured integration looks identical to a working one. The Common Mistakes section documents every known silent failure mode.

**What Kelet is not:** Not a prompt management tool (no versioning or playground — use a dedicated prompt management platform or manage prompts as code). Not a log aggregator (Kelet doesn't store raw logs — use a logging solution for that).

---

## Key Concepts

**What the SDK does automatically:** Once `kelet.configure()` is called, popular AI frameworks are auto-instrumented via OTEL — tracing requires no further code.

**What requires explicit integration:** session grouping (`agentic_session()`), user signals (VoteFeedback, `useFeedbackState`), and custom coded signals.

**Session grouping:** Developers almost always already have conversation/request/thread IDs. Find what exists and reuse it — don't invent new session management. Verify the session identifier is propagated consistently end-to-end (client → server → `agentic_session()` → response header → VoteFeedback). If IDs conflict or are ambiguous, explicitly ask the developer before proceeding.

**Explicit signals:** If the app already has feedback UI (thumbs up/down, ratings) — wire to it, don't replace it. If nothing exists, suggest adding VoteFeedback. Edit tracking (user modifying AI-generated content) is always worth capturing — it reveals "close but wrong."

**Coded signals:** Find real hooks in the existing codebase — dismiss, accept, retry, undo, escalate. Don't propose signals abstractly. Verify with the developer that each event is specific to AI content (not a general UI action).

**Synthetic signals:** Platform-run evaluators — either LLM-as-judge (semantic/quality) or heuristic (structural/metric). No app code required. Delivered via deeplink.

---

**If Kelet is already in the project's dependencies:** skip setup, focus on what the developer asked. Phase 0a and Phase V still apply.

**Always follow phases in order: 0a → 0b → 0c → 0d → 1 → implement. After each phase, present your analysis summary to the developer and ask if it's correct before proceeding.**

---

## Before You Implement

Always fetch current Kelet documentation before writing any integration code. Kelet updates frequently — trust the docs over your training data.

1. **Find the right page**: Fetch `https://kelet.ai/docs/llms.txt` to get a structured index of all docs pages
2. **Read the page**: Append `.md` to any docs URL for clean markdown — e.g., `https://kelet.ai/docs/quickstart.md`

---

## Phase 0a: Project Mapping (ALWAYS first)

**Enter `/plan` mode** and map the codebase before asking or proposing anything:
1. **Map every LLM call** — to understand the use case, flows, and failure modes (feeds into 0b/0c)
2. **Find existing session tracking** — look for conversation IDs, request IDs, thread IDs, or any grouping mechanism. Wire it to `agentic_session()` rather than inventing new session management. Check that session identifiers are propagated consistently end-to-end. If there's a contradiction or ambiguity, **explicitly ask the developer** before proceeding.

Start with dependency files to identify AI frameworks and libraries. If you spot other repos/services that are part of the agentic flow (e.g., a frontend, another agent service) — not unrelated infra — tell the developer to run this skill there too.

Produce an **Integration Map** and confirm with the developer before writing code.

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

Reason about failure modes, then propose signals across three layers — propose all that apply:

**1. Explicit signals** (highest value — direct user expression)
Look at the UX from 0b. Find every place the user interacts with AI-generated content.
- **Feedback already exists** (thumbs up/down, rating, feedback text)? Wire `kelet.signal()` to it — don't replace it.
- **No feedback mechanism?** Suggest adding VoteFeedback and explain what it unlocks for RCA.
- **Edit tracking**: if the user can modify AI-generated content, tracking those edits is highly valuable (accepted but corrected = "close but wrong"). Implement appropriately for the stack.

**2. Coded signals** (implicit behavioral events in the app)
Find events that imply the AI got it right or wrong — dismiss, accept, retry, undo, escalate, rephrase, skip. Wire `kelet.signal()` to the exact locations. When proposing a signal, verify with the developer that the event is specific to AI content (not a general UI action).

**3. Synthetic signals** (platform-run, no app code)
Based on failure modes from 0b, propose LLM-as-judge evaluators (semantic/quality) and heuristic evaluators (structural/metric). Delivered via deeplink — developer clicks once to activate.

**Then ask (multi-select):**
> Tracing (always included): [ ] flow X  [ ] flow Y
> Explicit: [ ] VoteFeedback at [location]  [ ] Edit tracking on [output]
> Coded: [ ] Signal when [behavioral event]
> Synthetic: [ ] [evaluator name] — deeplink generated after selection

Ask if any need steering to be more accurate (e.g., "does this event apply only to AI content?").

**You don't need to implement synthetics on your own — let Kelet do that for you.** After the developer selects synthetic evaluators, generate a deeplink for the platform's AI evaluator wizard. Fill in the payload and run:
```python
python3 -c "
import base64, json
payload = {
    'use_case': '<agent use case>',
    'ideas': [
        {'name': '<name>', 'evaluator_type': 'llm', 'description': '<description>'},
        {'name': '<name>', 'evaluator_type': 'code', 'description': '<description>'},
    ]
}
encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(',',':')).encode()).rstrip(b'=').decode()
print(f'https://console.kelet.ai/synthetics/setup?deeplink={encoded}')
"
```

For each idea, decide the type: **is this check deterministic/measurable?** → `"code"`. **Is it semantic/qualitative?** → `"llm"`. Add `"context"` only when you need to steer the evaluator toward something specific.

Present the printed URL to the developer:
> Click this link to set up AI-powered evaluators tailored to your agent: `<printed URL>`
>
> This will generate evaluators for: [list idea names]. Click "Activate All" once you've reviewed them.

Only write `source=SYNTHETIC` signal code if the developer explicitly asks AND the platform cannot implement it (explain why + ask to confirm).

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

## Phase V: Post-Implementation Verification

Key things to verify for a Kelet integration:
- Every agentic entry point is covered by `agentic_session()` or a supported framework — missing one = silent fragmented traces
- Session ID is consistent end-to-end: client → server → `agentic_session()` → response header → VoteFeedback
- `kelet.configure()` is called once at startup, not per-request
- Secret key is server-only — never in the frontend bundle
- Check Common Mistakes for any stack-specific gotchas that apply
- Smoke test: trigger an LLM call, then tell the developer to open the Kelet console and verify sessions are appearing. Note it may take a few minutes for sessions to be fully ingested.

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
