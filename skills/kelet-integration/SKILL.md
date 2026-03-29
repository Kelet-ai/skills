---
name: kelet-integration
description: >
  Integrates Kelet into AI applications end-to-end: instruments agentic flows with OTEL tracing, maps session
  boundaries, adds user feedback signals (VoteFeedback, edit tracking, coded behavioral hooks), generates
  synthetic signal evaluator deeplinks, and verifies the integration. Kelet is an AI agent that performs Root Cause
  Analysis on AI app failures — it ingests traces and signals, clusters failure patterns, and suggests fixes.
  Use when the developer mentions Kelet or asks to integrate, set up, instrument, or add tracing/signals/feedback
  to their AI app. Triggers on: "integrate Kelet", "set up Kelet", "add Kelet", "instrument my agent",
  "connect Kelet", "use Kelet".
license: CC-BY-4.0
metadata:
  author: kelet-ai
  url: https://kelet.ai
  version: "1.3.5"
---

# Kelet Integration

Kelet is an AI agent that does Root Cause Analysis for AI app failures. It ingests traces + user signals → clusters
failure patterns → generates hypotheses → suggests fixes. This skill integrates Kelet into a developer's AI application
end-to-end.

**Kelet never raise exceptions.** All SDK errors — misconfigured keys, network failures, wrong session IDs, missing
extras — are silenced to ensure QoS. A misconfigured integration looks identical to a working one. The Common
Mistakes section documents every known silent failure mode.

**What Kelet is not:** Not a prompt management tool (no prompt versioning or playground), and not a log aggregator (
doesn't store raw logs) — use other tools for those.

---

## Key Concepts

**What the SDK does automatically:** Once `kelet.configure()` is called, popular AI frameworks are auto-instrumented via
OTEL — tracing requires no further code.

**What requires explicit integration:** session grouping (`agentic_session()`), user signals (VoteFeedback,
`useFeedbackState`), and custom coded signals.

**Session grouping:** Developers almost always already have conversation/request/thread IDs. Find what exists and reuse
it — don't invent new session management. Verify the session identifier is propagated consistently end-to-end (client →
server → `agentic_session()` → response header → VoteFeedback). If IDs conflict or are ambiguous, explicitly ask the
developer before proceeding.

**Explicit signals:** If the app already has feedback UI (thumbs up/down, ratings) — wire to it, don't replace it. If
nothing exists, suggest adding VoteFeedback. Edit tracking (user modifying AI-generated content) is always worth
capturing — it reveals "close but wrong."

**Coded signals:** Find real hooks in the existing codebase — dismiss, accept, retry, undo, escalate. Don't propose
signals abstractly. Verify with the developer that each event is specific to AI content (not a general UI action).

**Synthetic signals:** Platform-run synthetic signal evaluators — either LLM-as-judge (semantic/quality) or heuristic (
structural/metric). No app code required. Delivered via deeplink.

---

**If Kelet is already in the project's dependencies:** skip setup, focus on what the developer asked. Phase 0a and Phase
V still apply.

**Always follow phases in order: 0a → 0b → 0c → 0d → 1 → implement. Each phase ends with a STOP: present your findings
to the developer and wait for confirmation before continuing. DO NOT chain phases silently. DO NOT write a full plan
without these checkpoints.**

**Plan mode:** This skill runs inside `/plan` mode. Present the full implementation plan and call `ExitPlanMode` for
approval BEFORE writing any code or editing any files. Never start implementation without explicit developer approval.

**Asking the developer:** Always use `AskUserQuestion` when you need input — never ask via free-form response text.
Use `multiSelect: true` for selection lists. This ensures questions are structured, answers are captured, and the
flow doesn't stall on ambiguous replies.

---

## Before You Implement

Always fetch current Kelet documentation before writing any integration code. Kelet updates frequently — trust the docs
over your training data.

1. **Ask the docs AI (preferred)**: `GET https://docs-ai.kelet.ai/chat?q=<your+question>` — returns a focused plain-text
   answer from live docs. Ask before writing code, e.g.:
    - `?q=how+to+configure+kelet+in+python`
    - `?q=agenticSession+typescript+usage`
    - `?q=VoteFeedback+session+id+propagation`
2. **Browse the index (fallback)**: If the AI answer is insufficient, fetch `https://kelet.ai/docs/llms.txt` for a
   structured index, then append `.md` to any docs URL for clean markdown — e.g.,
   `https://kelet.ai/docs/getting-started/quickstart.md`

---

## Phase 0a: Project Mapping (ALWAYS first)

**Enter `/plan` mode** and map the codebase before asking or proposing anything:

1. **Map every LLM call** — to understand the use case, flows, and failure modes (feeds into 0b/0c)
2. **Find existing session tracking** — look for conversation IDs, request IDs, thread IDs, or any grouping mechanism.
   Wire it to `agentic_session()` rather than inventing new session management. Check that session identifiers are
   propagated consistently end-to-end. If there's a contradiction or ambiguity, **explicitly ask the developer** before
   proceeding.

**Stay focused.** When exploring, only read what's relevant to Kelet: LLM calls, session IDs, startup/entrypoint code,
existing feedback UI, UI integration with the AI, and dependencies. Skip styling, animations, auth flows, unrelated
business logic — if it doesn't affect tracing or signals, ignore it. Our focus is to understand how the UI interacts
with the AI or the back-end that serves it.

Start with dependency files to identify AI frameworks and libraries. If you spot other repos/services that are part of
the agentic flow (e.g., a frontend, another agent service) — not unrelated infra — tell the developer to run this skill
there too.

Produce an **Integration Map**, present it to the developer, and **wait for confirmation** before proceeding to Phase
0b.

Infer from existing files (README, CLAUDE.md, entrypoints, dependency files, `.env`) before asking. Only ask what you
can't determine.

**Questions to resolve (ask only if unclear after reading files):**

1. What is the agentic use case?
2. How many distinct agentic flows? → maps to Kelet project count
   > A flow is isolated and standalone with clear ownership boundaries. If flow A triggers flow B with a clear interface
   boundary = TWO projects. Same flow in prod vs staging = TWO projects.
3. Is this user-facing? (determines whether React/VoteFeedback applies)
4. Stack: server (Python/Node.js/Next.js) + LLM framework + React?
5. Config and deployment infrastructure:
   > Writing keys to the wrong file is a silent failure. Critically, `.env` is local dev only — production secrets
   > must go through whatever real deployment channel the app uses.
   > Scan for deployment infra before asking:
   > - Helm / K8s: `helm/`, `charts/`, `values.yaml`, `deployment.yaml`, `configmap.yaml`, secret manifests
   > - GitHub Actions: `.github/workflows/*.yml`
   > - Vercel: `vercel.json`, `.vercel/`
   > - Railway: `railway.json`, `railway.toml`
   > - Render: `render.yaml`
   > - Fly.io: `fly.toml`
   > - Docker Compose: `docker-compose.yml`
   > - Heroku: `Procfile`, `app.json`
   > - AWS / IaC: `infra/`, `cdk/`, `*.tf`, `template.yaml`
   >
   > List every match. If nothing is found beyond `.env` / `.envrc`, flag as **deployment method: unknown** — you
   > will ask in Phase 1.
6. What is the exact Kelet project name for this flow?
   > Do NOT guess from the repo or app name — they differ. Projects are created from the **top-nav project switcher**
   > in console.kelet.ai (click the project name → New Project). Ask explicitly and wait for the developer's answer.
   > Mismatched project name is a silent failure — data captured under the wrong project with no error.

**Produce a Project Map before proceeding:**

```
Use case: [what the agents do]
Flows → Kelet projects:
  - flow "X" → project "X"
  - flow "Y" → project "Y"
User-facing: yes/no
Stack: [server framework] + [LLM framework]
Config: .env / .envrc / k8s
Deployment infra: [Helm | GH Actions | Vercel | Railway | Render | Fly.io | Docker Compose | Heroku | Terraform | none found]
```

---

## Phase 0b: Agentic Workflow + UX Mapping

The purpose of this phase is to map what "failure" looks like for Kelet's RCA engine — Kelet clusters spans by failure
pattern, so you need to understand failure modes before proposing signals.

**Workflow** (what the agent does):

- Steps and decision points
- Where it could go wrong: wrong retrieval, hallucination, off-topic, loops, timeouts
- What success vs. failure looks like from the agent's perspective

**UX** (if user-facing):

- What AI-generated content is shown? (answers, suggestions, code, summaries)
- Where do users react? (edit it, retry, copy, ignore, complain)
- What implicit behaviors signal dissatisfaction? (abandon, rephrase, undo)

Outputs from this phase feed directly into signal selection in 0c — each identified failure mode becomes a signal
candidate. Present the workflow + UX map to the developer and **wait for confirmation** before proceeding to Phase 0c.

---

## Phase 0c: Signal Brainstorming

Reason about failure modes, then propose signals across three layers — propose all that apply:

**1. Explicit signals** (highest value — direct user expression)
Look at the UX from 0b. Find every place the user interacts with AI-generated content.

- **Feedback already exists** (thumbs up/down, rating, feedback text)? Wire `kelet.signal()` to it — don't replace it.
- **No feedback mechanism?** Suggest adding VoteFeedback and explain what it unlocks for RCA.
- **Edit tracking**: if the user can modify AI-generated content, tracking those edits is highly valuable (accepted but
  corrected = "close but wrong"). Implement appropriately for the stack.

**2. Coded signals** (implicit behavioral events in the app)
Find events that imply the AI got it right or wrong — dismiss, accept, retry, undo, escalate, rephrase, skip. Wire
`kelet.signal()` to the exact locations. When proposing a signal, verify with the developer that the event is specific
to AI content (not a general UI action).

**3. Synthetic signals** (platform-run, no app code)
Based on failure modes from 0b, propose LLM-as-judge synthetic signal evaluators (semantic/quality) and heuristic
synthetic signal evaluators (structural/metric). Delivered LATER (after user approval) via deeplink — developer clicks
once to activate.

**Ground every synthetic signal evaluator in observed behavior.** Only propose synthetic signal evaluators for things
the agent actually does — don't invent features. If you're unsure whether the agent produces a certain output (e.g.
citations, confidence scores, structured data), ask the developer before proposing a synthetic signal evaluator that
depends on it. For `code` type: the check must be fully deterministic from the raw output (e.g. response length, JSON
validity, presence of a known token). If you're reaching for any natural language understanding, it's `llm`, not `code`.

**STOP — this is a REQUIRED interactive checkpoint.** Use `AskUserQuestion` with `multiSelect: true` — two questions:

1. One for explicit + coded signals (options = each proposed signal)
2. One for synthetic evaluators (options = each proposed evaluator)

Ask if any coded signals need steering (e.g., "does this event apply only to AI content?") and wait for their response.

**You don't need to implement synthetics on your own — let Kelet do that for you.** After the developer has selected
which synthetic evaluators they want, generate the deeplink scoped to exactly those evaluators and present it as a bold
standalone action item:

> **Action required → click this link to activate your synthetic evaluators:**
> `https://console.kelet.ai/synthetics/setup?deeplink=<encoded>`
>
> This will generate evaluators for: [list selected names]. Click "Activate All" once you've reviewed them.

Generate the deeplink like this — include only the evaluators the developer selected:

```python
python3 - c
"
import base64, json

payload = {
    'use_case': '<agent use case>',
    'ideas': [
        {'name': '<name>', 'evaluator_type': 'llm', 'description': '<description>'},
        {'name': '<name>', 'evaluator_type': 'code', 'description': '<description>'},
    ]
}
encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(',', ':')).encode()).rstrip(b'=').decode()
print(f'https://console.kelet.ai/synthetics/setup?deeplink={encoded}')
"
```

ONLY create and send the link AFTER the developer has selected which evaluators they want. Do NOT generate or present
the link before they make their selection — that would be confusing and overwhelming. The link should reflect their
choices, not all possible ideas!

For each idea, decide the type: **is this check deterministic/measurable?** → `"code"`. **Is it semantic/qualitative?**
→ `"llm"`. Add `"context"` only when you need to steer the evaluator toward something specific.

After presenting the link, use `AskUserQuestion` to confirm the developer has clicked it and activated the evaluators
before proceeding to Phase 0d. Do NOT proceed until confirmed.

Only write `source=SYNTHETIC` signal code if the developer explicitly asks AND the platform cannot implement it (explain
why + ask to confirm).

See [references/signals.md](references/signals.md) for signal kinds, sources, and when to use each.

---

## Phase 0d: What You'll See in Kelet

| After implementing                | Visible in Kelet console                                                 |
|-----------------------------------|--------------------------------------------------------------------------|
| `kelet.configure()`               | LLM spans in Traces: model, tokens, latency, errors                      |
| `agentic_session()`               | Sessions view: full conversation grouped for RCA                         |
| VoteFeedback                      | Signals: 👍/👎 correlated to the exact trace that generated the response |
| Edit signals (`useFeedbackState`) | Signals: what users corrected — reveals model errors                     |
| Platform synthetics               | Signals: automated quality scores Kelet runs on your behalf              |

---

## Sessions

A session is the logical boundary of one unit of work — all LLM calls, tool uses, agent hops, and retrievals that belong
to the same context. Not tied to conversations: a batch processing job, a scheduled pipeline, or a chat thread are all
valid sessions. New context = new session.

**The framework orchestrates the flow** (pydantic-ai runs your agent loop, LangGraph manages your graph execution, a
LangChain chain runs end-to-end): Kelet infers sessions automatically — no `agentic_session()` needed. Supported
frameworks: pydantic-ai, LangChain/LangGraph, LlamaIndex, CrewAI, Haystack, DSPy, LiteLLM, Langfuse, and any framework
using OpenInference or OpenLLMetry instrumentation. If the framework isn't listed, research whether it uses one of these
instrumentation libraries before omitting `agentic_session()`.

**Exception — externally managed session lifecycle:** If the app owns the session ID (e.g. stored in Redis, a database,
or generated server-side and returned to the client), the framework has no knowledge of it. You MUST use
`agentic_session(session_id=...)` even with a supported framework — otherwise Kelet generates its own session ID that
doesn't match the one the client receives, breaking VoteFeedback linkage.

Note: **Vercel AI SDK does not set session IDs automatically** — use `agenticSession()` at the route level (see Next.js
section).

**You own the loop** (you write the code that calls agent A, passes results to agent B, chains steps in Temporal, a
custom loop, or any orchestrator you built — even if individual steps use a supported framework internally): the
framework doesn't set a session ID for the overall flow. You MUST use `agentic_session(session_id=...)` /
`agenticSession({ sessionId }, callback)`. (**Silent if omitted — spans appear as unlinked individual traces.**)

---

## Phase 1: API Key Setup

Two key types — never mix them:

- **Secret key** (`KELET_API_KEY`): server-only. Traces LLM calls. Never expose to frontend.
- **Publishable key** (`VITE_KELET_PUBLISHABLE_KEY` / `NEXT_PUBLIC_KELET_PUBLISHABLE_KEY`): frontend-safe. Used in
  `KeletProvider` for VoteFeedback widget.

**Ask for API keys during planning** (before presenting the final plan / calling ExitPlanMode). Use `AskUserQuestion`
(with an "I'll paste it in Other" option) to collect each key interactively. If the developer says they don't have a
key or don't know what it is, direct them to create one:
> Go to **https://console.kelet.ai/api-keys** to create your key, then paste it here.

Do not proceed until both required keys are in hand (or explicitly deferred with a placeholder).

**Project name workflow:**

1. Suggest a name based on the app (e.g. "docs-ai" → "docs_ai_prod").
2. Instruct: "Create this project in the Kelet console — click the project name in the **top-nav** at
   console.kelet.ai, then 'New Project'. Use the name `<suggested_name>`."
3. Ask (`AskUserQuestion`): "Have you created the project? What is the exact name you used?" — wait for their answer.
4. If not created or using default: omit `project=` entirely — Kelet routes to the default project automatically.
5. Once confirmed: write to env file as `KELET_PROJECT` (server) and `PUBLIC_KELET_PROJECT` / `VITE_KELET_PROJECT`
   (frontend). Read in code via env var — **never hardcode the project name string in source files.**

Once received, write to the correct file based on the detected config pattern:

- `.env` → `KEY=value`
- `.envrc` (direnv) → `export KEY=value`
- K8s → tell developer to add to secrets manifest

Add both vars to `.gitignore` if not already present.

**Production secrets — `.env` is local dev only.** Every key written above must also reach the production
environment. Based on deployment infra found in Phase 0a, follow
[references/deployment.md](references/deployment.md) for platform-specific steps. Confirm completion with
`AskUserQuestion` before proceeding — an unconfirmed step is a silent failure.

**If deployment method is unknown** (nothing found beyond `.env`/`.envrc`): use `AskUserQuestion` —
"How do you deploy this app to production? How are env vars / secrets managed there?" — and wait for their answer
before continuing.

---

## Implementation: Key Concepts by Stack

See [references/api.md](references/api.md) for exact function signatures and package names.
See [references/stack-notes.md](references/stack-notes.md) for full per-stack details, gotchas, and code patterns.

**Python**: `kelet.configure()` at startup; `agentic_session()` required when you own the orchestration loop
(supported frameworks infer sessions automatically). Streaming: wrap the entire generator body — see stack-notes.md.

**TypeScript/Node.js**: `agenticSession` is **callback-based** (not a context manager) — see stack-notes.md for the
critical difference. Requires OTEL peer deps alongside `kelet`.

**Next.js**: `KeletExporter` in `instrumentation.ts` via `@vercel/otel`. Two configs commonly missed (both **silent**
if omitted) — see stack-notes.md.

**Multi-project / React**: one `configure()` call, per-session `project=` override; `KeletProvider` at app root.
No-React frontend? Present options before proceeding — see stack-notes.md.

**Which feedback hook to use:**

- Explicit rating of AI response → `VoteFeedback`
- Editable AI output → `useFeedbackState` with trigger names
- Coded behavioral events (abandon, retry, copy) → `useKeletSignal()`

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
├─► Explicit (votes)            ──► VoteFeedback / kelet.signal(kind=FEEDBACK, source=HUMAN)
├─► Implicit (edits)            ──► useFeedbackState (tag AI vs human updates with trigger names)
├─► Coded signals from React    ──► useKeletSignal() inside KeletProvider
└─► Synthetic signal evaluators ──► Generate deeplink → console.kelet.ai/synthetics/setup
```

---

## Implementation Steps

1. **Project Map** — infer from files, confirm flow → project mapping
2. **API keys** — ask for keys, detect config pattern, write to correct file
3. **Install** — Python: `kelet[all]` or per-library extras. Node.js/Next.js: `kelet` + OTEL peer deps (
   `@opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-http`) — Python needs no OTEL
   deps. React: `@kelet-ai/feedback-ui`
4. **Instrument server** — `configure()` at startup + `agentic_session()` per flow
5. **Instrument frontend** — `KeletProvider` at root, nested per flow if multi-project
6. **Connect feedback** — VoteFeedback + session ID propagation if user-facing
7. **Verify** — type check, confirm env vars set, open Kelet console and confirm traces appear

---

## Phase V: Post-Implementation Verification

Key things to verify for a Kelet integration:

- Every agentic entry point is covered by `agentic_session()` or a supported framework — missing one = silent fragmented
  traces
- Session ID is consistent end-to-end: client → server → `agentic_session()` → response header → VoteFeedback
- `kelet.configure()` is called once at startup, not per-request
- Secret key is server-only — never in the frontend bundle
- Check [references/common-mistakes.md](references/common-mistakes.md) for silent failure modes specific to the detected
  stack
- Smoke test: trigger an LLM call, then tell the developer to open the Kelet console and verify sessions are appearing.
  Note it may take a few minutes for sessions to be fully ingested.
- If VoteFeedback was added: use the available browser tool (chrome devtools MCP or browsermcp) to take a screenshot
  of the feedback bar. Verify it looks on-brand and matches the app's design language. Also confirm:
  `document.querySelectorAll('button button').length === 0` (no nested buttons). Do not rely on "build passes" alone —
  headless UI requires visual verification.
- After ANY frontend changes: screenshot existing pages (not just the new feature) to verify they still render
  correctly. tsconfig overrides or invalid HTML can silently break unrelated pages — build passing ≠ pages unaffected.

---

## Common Mistakes

See [references/common-mistakes.md](references/common-mistakes.md) for the full table of silent failure modes.
Review during Phase V, checking every entry that applies to the detected stack.
