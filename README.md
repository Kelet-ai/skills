# Kelet Agent Skills

**Two steps to get Kelet working in your AI app:**

1. [Sign up at console.kelet.ai](https://console.kelet.ai)
2. Install this skill and tell your agent: `Integrate Kelet into my app`

That's it. The skill handles everything else.

---

Kelet is an AI agent that does Root Cause Analysis for AI agent failures: it analyzes production traces and signals at scale to tell you what's failing, why, and how to fix it — so you don't spend hours scrolling through traces manually.

The `kelet-integration` skill teaches your coding agent how to instrument your app end-to-end: it maps your agentic flows, proposes failure-mode-specific signals, sets up API keys, writes the instrumentation code, and generates a one-click link to set up automated AI evaluators tailored to your agent.

## Installation

### Claude Code

```
/plugin marketplace add Kelet-ai/skills
/plugin install kelet-integration@kelet-skills
```

### Other agents (Cursor, Copilot, Windsurf, Cline, and more)

Via [skills.sh](https://skills.sh) — works with 20+ agents:

```bash
npx skills add Kelet-ai/skills
# or:
bunx skills add Kelet-ai/skills
```

### Manual

Clone this repo and copy `skills/kelet-integration/` into your agent's skills directory.

## Usage

Once installed, just mention Kelet in your prompt:

```
Integrate Kelet into my FastAPI app
Add Kelet tracing and user feedback to my Next.js project
Set up Kelet for my multi-agent system
```

## What You Get

- **Traces** — every LLM call, token count, latency, and error captured automatically
- **Sessions** — traces grouped by conversation for full RCA context
- **Signals** — user feedback (👍/👎, edits) correlated to the exact trace that produced the response
- **Synthetic evaluators** — AI-generated quality checks tailored to your agent's failure modes, one click to activate
- **Issues** — Kelet clusters failure patterns and generates root cause hypotheses automatically

## Links

- [Kelet Platform](https://kelet.ai)
- [Console](https://console.kelet.ai)
- [Python SDK](https://github.com/Kelet-ai/python-sdk)
- [TypeScript SDK](https://github.com/Kelet-ai/typescript-sdk)
- [Agent Skills spec](https://agentskills.io/specification)

## License

[CC BY 4.0](LICENSE)
