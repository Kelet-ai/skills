# Kelet Stack Implementation Notes

## Contents

- [Python](#python): `kelet.agent()`, streaming pattern
- [TypeScript/Node.js](#typescriptnodejs): callback-based `agenticSession`, OTEL peers
- [Next.js](#nextjs): `KeletExporter`, two silent configs
- [Multi-project apps](#multi-project-apps)
- [React](#react): `KeletProvider` nesting
- [No-React frontends](#no-react-frontends): options table
- [VoteFeedback: session ID propagation](#votefeedback-session-id-propagation)
- [useFeedbackState and useKeletSignal](#usefeedbackstate-and-usekeletsignal)

---

## Python

`kelet.configure()` at startup auto-instruments pydantic-ai/Anthropic/OpenAI/LangChain — no extras needed.
All params default to env vars; `kelet.configure()` with no args works when `KELET_API_KEY` is set.
`agentic_session()` is **required whenever you own the orchestration loop**. If a supported framework orchestrates for
you, sessions are inferred automatically — no wrapper needed. See Sessions section in SKILL.md.

`kelet.agent(name=...)` — use when: (a) multiple agents run in one session and need separate attribution, or (b) your
framework doesn't expose agent names natively (pydantic-ai does; OpenAI/Anthropic/raw SDKs don't — Kelet can't infer
it). Logfire users: `kelet.configure()` detects the existing `TracerProvider` — no conflict.

**Bare LiteLLM:** traces are auto-captured, but LiteLLM does not natively propagate session/agent context into its
spans. If LiteLLM is called directly (not through another instrumented framework like Google ADK), wrap calls in
`agentic_session()` (and optionally `kelet.agent()`) to group them. When LiteLLM runs under another framework that
sets context, no extra wrapping is needed.

**Streaming:** wrap the **entire** generator body (not the caller), including the final sentinel — trailing spans are
silently lost otherwise:

```python
async def stream_response():
    async with kelet.agentic_session(session_id=...):
        async for chunk in llm.stream(...):  # sentinel included in scope
            yield chunk
```

---

## TypeScript/Node.js

`agenticSession` is **callback-based** (not a context manager). AsyncLocalStorage context propagates through the
callback's call tree — there's no `with`-equivalent in Node.js, so the callback IS the scope boundary. Node.js only
(not browser-compatible). Writing `await agenticSession(...)` without a callback silently breaks context propagation.

```
agenticSession({ sessionId, userId? }, async () => { ... })  // returns callback's return value
```

Requires OTEL peer deps alongside `kelet`:

```
@opentelemetry/api @opentelemetry/sdk-trace-node @opentelemetry/exporter-trace-otlp-http
```

---

## Next.js

Use `KeletExporter` in `instrumentation.ts` via `@vercel/otel`:

```ts
new KeletExporter({apiKey, project})
```

Two required steps often missed (both **silent** if omitted):

1. `experimental: { instrumentationHook: true }` in `next.config.js` — without it, `instrumentation.ts` never runs.
2. Each Vercel AI SDK call needs `experimental_telemetry: { isEnabled: true }` — telemetry is off by default.

**Vercel AI SDK does not set session IDs automatically** — use `agenticSession()` at the route level.

---

## Multi-project Apps

Call `configure()` once with no project. Override per call with `agentic_session(project=...)`. W3C Baggage
propagates the project to downstream microservices automatically.

---

## React

`KeletProvider` at app root sets `apiKey` + default project. For multiple AI features belonging to different Kelet
projects: nest a second `KeletProvider` with only `project=` — it inherits `apiKey` from the outer provider. No need
to repeat the key.

---

## No-React Frontends

VoteFeedback requires React. Before concluding "no React = no VoteFeedback", check if the framework supports React
interop (Astro via `@astrojs/react`, SvelteKit via `svelte-preprocess`, etc.). This is a major architectural decision
— present the tradeoffs and let the developer choose before proceeding:

| Option                                              | Trade-offs                                                                                                                                                      |
|-----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Add React (recommended)** — e.g. `@astrojs/react` | Official SDK, best integration, richer UX — adds React as a dependency but most frameworks support React islands/interop                                        |
| Implement feedback UI ad hoc in the existing stack  | No new dependencies — VoteFeedback is conceptually just 👍/👎 buttons that POST a signal to the Kelet REST API. Valid if adding React is genuinely not feasible |
| Skip frontend feedback for now                      | Fastest — server-side tracing still works; add feedback later                                                                                                   |

Do not assume — always present the options and let them choose.

---

## VoteFeedback: Session ID Propagation

`session_id` passed to `VoteFeedback.Root` must exactly match what the server used in `agentic_session()`. If they
differ, feedback is captured but **silently unlinked** from the trace.

End-to-end flow:
Client generates UUID → sends in request body → server uses in `agentic_session(session_id=...)` → server returns it
as `X-Session-ID` response header → client passes it to `VoteFeedback.Root`.

---

## useFeedbackState and useKeletSignal

**`useFeedbackState`**: drop-in for `useState`. Each `setState` call accepts a trigger name as second arg — tag
AI-generated updates `"ai_generation"` and user edits `"manual_refinement"`. Without trigger names, all state changes
look identical and Kelet can't distinguish "user accepted AI output" from "user corrected it."

**`useKeletSignal()`**: returns a `sendSignal(params)` function for sending signals directly from React event
handlers — abandon, rephrase, accept, copy. Must be inside `KeletProvider`. Preferred over a backend endpoint for
browser-observable events (no round-trip needed).
