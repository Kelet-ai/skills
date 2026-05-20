# Kelet Stack Implementation Notes

## Contents

- [Python](#python): `kelet.agent()`, streaming pattern
- [TypeScript/Node.js](#typescriptnodejs): callback-based `agenticSession`, OTEL peers
- [Next.js](#nextjs): `KeletExporter`, two silent configs
- [Temporal](#temporal): `KeletPlugin`, plugin propagation rules
- [Claude Agent SDK](#claude-agent-sdk): auto env-injection, ESM caveats
- [Multi-project apps](#multi-project-apps)
- [React](#react): `KeletProvider` nesting
- [No-React frontends](#no-react-frontends): options table
- [VoteFeedback: session ID propagation](#votefeedback-session-id-propagation)
- [useFeedbackState and useKeletSignal](#usefeedbackstate-and-usekeletsignal)

---

## Python

`kelet.configure()` at startup auto-instruments pydantic-ai/Anthropic/OpenAI/LangChain — spans capture, but the
session ID is only inferred when the framework owns it.
All params default to env vars; `kelet.configure()` with no args works when `KELET_API_KEY` is set.
`agentic_session(session_id=...)` is **required whenever the app owns the session ID** (Redis/DB/server-issued UUID)
or you own the orchestration loop — auto-instrumentation alone can't link your ID to spans. Wrap at the route/handler
that bounds the conversation. See Sessions section in SKILL.md.

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

## Temporal

`KeletPlugin` propagates session context through Temporal headers across `start_workflow → workflow → child workflow → activity` so `kelet.signal()` and instrumentation auto-resolve the session inside activities without arg-threading. Register on the client; bundles Temporal's own `OpenTelemetryPlugin` by default so OTel trace context links workflow + activity spans.

**Install:** `kelet[temporal]` (Python) / `kelet @temporalio/plugin @temporalio/interceptors-opentelemetry` (TypeScript).

**Python:**

```python
from kelet.temporal import KeletPlugin
from temporalio.client import Client

client = await Client.connect("localhost:7233", plugins=[KeletPlugin()])
# Workers built from this client inherit the plugin automatically.

async with kelet.agentic_session(session_id="conv-42"):
    await client.execute_workflow(MyWorkflow.run, ..., id="wf-1", task_queue="ai")
```

**TypeScript:**

```ts
import { KeletPlugin } from 'kelet/temporal';
import { Client } from '@temporalio/client';
import { Worker } from '@temporalio/worker';

const plugin = new KeletPlugin({ otelPluginOptions: { resource, spanProcessor } });
const client = new Client({ /* ... */, plugins: [plugin] });
const worker = await Worker.create({ /* ... */, plugins: [plugin] });
```

**Plugin propagation differs between SDKs (silent if forgotten):**
- **Python**: registering on the client auto-applies to every `Worker` constructed from that client.
- **TypeScript**: the TS SDK doesn't auto-propagate plugins from `Client` to `Worker` — pass `plugins: [plugin]` to **both**. Same plugin instance can be reused.

**Plugin ordering with user-managed OTel:** Kelet bundles `OpenTelemetryPlugin` by default and detects pre-existing OTel via the `[OTel, Kelet]` order — register your own OTel plugin **before** `KeletPlugin` and Kelet skips its bundled OTel. Inverse order (`[Kelet, OTel]`) won't be detected and produces duplicate OTel spans — set `include_otel_plugin=False` (Py) / `includeOtelPlugin: false` (TS) when you must register Kelet first.

**`kelet.signal()` from workflow code:** `KeletPlugin` auto-registers a `_kelet_signal` activity. From workflow code, `kelet.signal()` transparently dispatches through it (HTTP from workflows is non-deterministic). Configure failure behavior with `kelet.configure(signal_failure_mode="swallow"|"raise")` — default `swallow` so telemetry never fails workflows. **Critical:** if a user wires the standalone `KeletInterceptor` (without `KeletPlugin`), the activity is not registered — calling `signal()` from a workflow raises a clear `RuntimeError` pointing at the fix.

**`agentic_session()` inside workflow code:** auto-detects the workflow sandbox and runs in lite mode (contextvars only — no OTel baggage attach, no background drain, both non-deterministic). Behavior outside workflows is unchanged.

**`auto_session` callable must be deterministic:** runs on the workflow side and is invoked during initial execution AND replay. Non-deterministic resolvers (reading `datetime.now()`, making HTTP calls) cause workflow non-determinism failures and block the workflow. Pure resolvers only.

**TypeScript: `autoSession` is client-side only.** Workflows started via Temporal CLI / schedules / non-TS clients won't get a session header. Use `activityAutoSession` as a worker-side backstop. Python's `auto_session` runs on the workflow inbound side, so it covers all start paths.

Full reference: [docs.kelet.ai/integrations/temporal](https://docs.kelet.ai/docs/integrations/temporal/).

---

## Claude Agent SDK

`@anthropic-ai/claude-agent-sdk` (Python `claude-agent-sdk` / TS `@anthropic-ai/claude-agent-sdk`) spawns a `claude` CLI subprocess for each `query()` / `ClaudeSDKClient` call. Claude Code emits OTLP traces, logs, and metrics when seven env vars are set: `CLAUDE_CODE_ENABLE_TELEMETRY`, `OTEL_LOGS_EXPORTER`, `OTEL_METRICS_EXPORTER`, `OTEL_TRACES_EXPORTER`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`. Without those, **zero traffic** lands at Kelet — silent failure mode.

**Install:** `kelet[claude-agent-sdk]` (Python) / `kelet` plus optional `@opentelemetry/sdk-logs @opentelemetry/exporter-logs-otlp-http @opentelemetry/api-logs` (TypeScript, only needed for reasoning capture).

**Python — fully automatic:**

```python
import kelet

kelet.configure(api_key="...", project="my-agent")  # wraps query + ClaudeSDKClient

from claude_agent_sdk import query  # import AFTER configure() so the wrap is visible

async for msg in query(prompt="hello"):
    ...
```

The wrap injects the seven keys into `ClaudeAgentOptions.env` per call — never touches `os.environ`, so the host process's other OTel pipelines stay intact. Override on conflict (subprocess scope only) + warn-once.

**Python — import order:** `kelet.configure()` must run before `from claude_agent_sdk import query` for the wrap to take effect on the module-level `query` symbol. `ClaudeSDKClient` is patched at the class level — order-independent.

**TypeScript — Layer A (process.env, default path):**

```typescript
import { configure } from 'kelet';
configure({ apiKey: process.env.KELET_API_KEY!, project: 'my-agent' });

import { query } from '@anthropic-ai/claude-agent-sdk';
```

`configure()` populates `process.env` set-if-missing. **Defers** to existing values (warn-once) — never overrides, because the mutation is process-wide.

**TypeScript — Layer B (when user passes `options.env`):** the `claude` JS SDK uses `m6 ? {...m6} : {...process.env}` — passing `options.env` REPLACES `process.env` instead of merging. ESM bindings are frozen, so `configure()` cannot patch `query` post-import. Use:

- **Loader (Node/tsx):** `node --import kelet/claude-agent-sdk/register app.js`
- **Drop-in shim (Bun, all runtimes):** `import { query, ClaudeSDKClient } from 'kelet/claude-agent-sdk/shim'`

Both wire Kelet's seven keys into `options.env` set-if-missing on every call.

**Opt out:** `inject_cc_telemetry=False` (Python) / `injectCcTelemetry: false` (TS). If you opt out and don't set `CLAUDE_CODE_ENABLE_TELEMETRY=1` yourself, the SDK emits a one-shot info log so the silent-failure mode is visible.

**Reasoning capture:** Kelet emits `kelet.reasoning` log records (scope `com.anthropic.claude_code.kelet_reasoning`) for each redacted ThinkingBlock yielded by `query()` / `receive_messages` / `receive_response`. Attributes: `reasoning.text`, `reasoning.signature`, `reasoning.message_id`, `session.id`. TypeScript reasoning capture requires the optional OTLP-logs peer deps; without them, env injection still works.

Full reference: [docs.kelet.ai/integrations/claude-agent-sdk](https://docs.kelet.ai/docs/integrations/claude-agent-sdk/).

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
handlers — abandon, accept, copy (explicit-trigger only; rephrase belongs to the LLM synthetic layer, not here).
Must be inside `KeletProvider`. Preferred over a backend endpoint for browser-observable events (no round-trip needed).
