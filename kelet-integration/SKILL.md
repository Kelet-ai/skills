---
name: kelet-integration
description: Use when integrating Kelet into an AI application — setting up tracing, user feedback collection, and session correlation across Python, TypeScript/Node.js, Next.js, and React frontends. Triggers on requests to "add Kelet", "instrument my agent", "set up Kelet tracing", "add feedback collection", or "integrate with Kelet".
---

# Kelet Integration

Kelet is an AI agent that does Root Cause Analysis for AI app failures. It ingests traces + user signals → clusters failure patterns → generates hypotheses → suggests fixes. This skill integrates Kelet into a developer's AI application end-to-end.

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

Map each agentic flow before deciding what to instrument.

**Workflow** (what the agent does):
- Steps and decision points
- Where it could go wrong: wrong retrieval, hallucination, off-topic, loops, timeouts
- What success vs. failure looks like from the agent's perspective

**UX** (if user-facing):
- What AI-generated content is shown? (answers, suggestions, code, summaries)
- Where do users react? (edit it, retry, copy, ignore, complain)
- What implicit behaviors signal dissatisfaction? (abandon, rephrase, undo)

---

## Phase 0c: Signal Brainstorming

Reason about failure modes, then propose specific signals — not a generic list.

**Thinking process per flow:**
1. What does a bad output look like at each step?
2. Would the user notice immediately or only after consequences?
3. What would they do when they notice? (edit, retry, abandon)
4. Can it be detected automatically? (API error, timeout, output quality)

**Propose 3–5 signals per flow** (cap at 5 — focus on highest signal-to-noise). For each: what it captures, how it manifests, what failure it reveals to Kelet's RCA engine.

**CRITICAL: Synthetic signals are the platform's responsibility.**
If the developer asks about LLM-as-judge or automated quality metrics → point them to `https://console.kelet.ai/synthetics`. Kelet manages evaluators there on their behalf. Only write `source=SYNTHETIC` signal code if the developer explicitly asks AND the platform cannot implement it (explain why + ask to confirm).

**Multi-select ask:**
> "Here are the most valuable signals for your workflow. Select what to implement:"
>
> Tracing (always included): [ ] flow X  [ ] flow Y
> Explicit feedback: [ ] VoteFeedback at [location] — "was this helpful?"
> Implicit feedback: [ ] Edit tracking on [editable output] — "user corrected this"
> Automated: [ ] Signal when [condition] — e.g., tool call fails, output rejected
>
> Platform synthetics (set up at console.kelet.ai/synthetics): [ ] LLM-as-judge for [quality concern]

See [reference/signals.md](reference/signals.md) for signal kinds, sources, and when to use each.

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

See [reference/api.md](reference/api.md) for exact function names, package names, and the one TS gotcha.

**Python**: `kelet.configure()` at startup (reads `KELET_API_KEY`, raises `ValueError` if missing, auto-instruments pydantic-ai/Anthropic/OpenAI/LangChain). Wrap each AI call with `agentic_session(session_id=..., project=...)`. For multi-agent flows, use `kelet.agent(name=...)` to name each agent — readable traces. Streaming: wrap the **entire** generator body including final sentinel or trailing spans are silently lost. Logfire users: `kelet.configure()` detects the existing `TracerProvider` and adds its processor — no conflict.

**TypeScript/Node.js**: `agenticSession` is **callback-based** (not a context manager) — this is the one non-obvious difference. Uses `AsyncLocalStorage`, Node.js only.

**Next.js**: `KeletExporter` in `instrumentation.ts` via `@vercel/otel`.

**Multi-project apps**: Call `configure()` once with no project. Override per call with `agentic_session(project=...)`. W3C Baggage propagates the project to downstream microservices automatically.

**React**: `KeletProvider` at app root sets `apiKey` + default project. For multiple AI features belonging to different Kelet projects: nest a second `KeletProvider` with only `project=` — it inherits `apiKey` from the outer provider. No need to repeat the key.

**VoteFeedback**: `session_id` passed to `VoteFeedback.Root` must exactly match what the server used in `agentic_session()`. If they differ, feedback is captured but silently unlinked from the trace.

**Session ID propagation** (how feedback links to traces):
Client generates UUID → sends in request body → server uses in `agentic_session(session_id=...)` → server returns it as `X-Session-ID` response header → client passes it to `VoteFeedback.Root`. This is what correlates the user's vote to the LLM call that produced the response.

**Edit signals**: `useFeedbackState(initialState, session_id)` is a drop-in for `useState`. It automatically tracks user edits to AI-generated content as implicit feedback signals.

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
├─► Explicit (votes)  ──► VoteFeedback / kelet.signal(kind=FEEDBACK, source=HUMAN)
├─► Implicit (edits)  ──► useFeedbackState
└─► Automated metrics ──► Platform synthetics → console.kelet.ai/synthetics
```

---

## Implementation Steps

1. **Project Map** — infer from files, confirm flow → project mapping
2. **API keys** — ask for keys, detect config pattern, write to correct file
3. **Install** — `kelet` (server), `@kelet-ai/feedback-ui` (React)
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
