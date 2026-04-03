# Implementation Reference

## Session ID Evaluation

Before choosing a session ID, answer from the code:

```
Does the app have a new-conversation / reset / start-over concept?
├─► Yes: does the candidate ID change at that boundary?
│   ├─► Yes ──► ✅ Correct mapping — proceed
│   └─► No  ──► ⚠️ Mismatch — surface it, propose a fix (e.g. generate UUID per conversation)
└─► No reset concept found / ambiguous ──► Ask developer to confirm intended session boundary

Is the candidate ID a stable user identifier (phone, email, user_id, device_id)?
└─► Yes ──► ⚠️ It outlives sessions — use as user_id=, generate kelet_session_id UUID per conversation
```

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

## Implementation Steps

1. **Project Map** — infer from files, confirm flow → project mapping
2. **API keys** — ask for keys, detect config pattern, write to correct file. Always write `KELET_PROJECT`
   (use `default` if not using a custom project) — explicit is better than implicit
3. **Install** — detect package manager from lockfiles/config (`uv.lock`/`pyproject.toml` → uv,
   `poetry.lock` → poetry, `Pipfile` → pipenv, else pip; `bun.lockb` → bun, `pnpm-lock.yaml` → pnpm,
   `yarn.lock` → yarn, else npm). Python: install `kelet` (no extras). Node.js/Next.js: install `kelet` +
   OTEL peer deps (`@opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-http`).
   React: install `@kelet-ai/feedback-ui`.
4. **Instrument server** — `configure()` at startup + `agentic_session()` per flow
5. **Instrument frontend** — `KeletProvider` at root, nested per flow if multi-project
6. **Connect feedback** — VoteFeedback + session ID propagation if user-facing
7. **Verify** — type check, confirm env vars set, open Kelet console and confirm traces appear
