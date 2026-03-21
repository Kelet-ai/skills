# Kelet Agent Skills

[Claude Code](https://claude.ai/code) skills for integrating [Kelet](https://kelet.ai) into AI applications.

Kelet is an AI agent that does Root Cause Analysis for AI agent failures: it analyzes production traces and user signals at scale to tell you what's failing, why, and how to fix it — so you don't spend hours scrolling through traces manually.

These skills teach Claude how to instrument your app with Kelet end-to-end.

## Skills

| Skill | Description |
|---|---|
| [`kelet-integration`](skills/kelet-integration/) | Interactively integrates Kelet into an AI app: maps agentic flows, brainstorms failure-mode-specific signals, sets up API keys, and writes the instrumentation code. Covers Python, TypeScript/Node.js, Next.js, and React. |

## Installation

### Claude Code

Add the Kelet marketplace and install the skill:

```
/plugin marketplace add Kelet-ai/skills
/plugin install kelet-integration@kelet-skills
```

### Manual

Clone this repo and point Claude Code to the `skills/` directory in your plugin settings.

## Usage

Once installed, just mention Kelet in your prompt:

```
Integrate Kelet into my FastAPI app
Add Kelet tracing and user feedback to my Next.js project
Set up Kelet for my multi-agent system
```

The skill walks through your project interactively — mapping your agentic flows, proposing signals specific to your failure modes, and writing the integration code.

## What You Get

After integrating with the `kelet-integration` skill:

- **Traces** — every LLM call, token count, latency, and error captured automatically
- **Sessions** — traces grouped by conversation for full RCA context
- **Signals** — user feedback (👍/👎, edits) correlated to the exact trace that produced the response
- **Issues** — Kelet clusters failure patterns and generates root cause hypotheses automatically

[Sign up at console.kelet.ai →](https://console.kelet.ai)

## Links

- [Kelet Platform](https://kelet.ai)
- [Console](https://console.kelet.ai)
- [Python SDK](https://github.com/Kelet-ai/python-sdk)
- [TypeScript SDK](https://github.com/Kelet-ai/typescript-sdk)
- [Agent Skills spec](https://agentskills.io/specification)

## License

MIT
