# Kelet Agent Skills

Claude Code skills for integrating [Kelet](https://kelet.ai) — automated Root Cause Analysis for AI agent failures — into your AI applications.

## Available Skills

### `kelet-integration`

Interactively instruments your AI application with Kelet end-to-end: maps your agentic flows, brainstorms failure-mode-specific signals, sets up API keys, and writes the integration code.

**Covers:** Python (pydantic-ai/FastAPI), TypeScript/Node.js, Next.js, React frontend (KeletProvider + VoteFeedback widget), session ID propagation.

## Installation

### Claude Code

```bash
/plugin install kelet-integration@kelet-skills
```

Or add as a marketplace:

```bash
/plugin marketplace add Kelet-ai/skills
```

Then install a skill:

```
/plugin install kelet-integration@kelet-skills
```

### Manual

Clone this repo and load the skill directory directly in Claude Code settings.

## Usage

Once installed, mention Kelet in your prompt:

> "Integrate Kelet into my FastAPI app"
> "Add Kelet tracing to my Next.js project"
> "Set up user feedback collection with Kelet"

The skill will walk you through the full integration interactively.

## What is Kelet?

Kelet analyzes your AI agent's production traces + user signals to automatically identify failure patterns, generate root cause hypotheses, and suggest prompt fixes — so you don't have to scroll through 10,000 traces manually.

- [Sign up](https://console.kelet.ai)
- [Documentation](https://docs.kelet.ai)
- [Python SDK](https://github.com/Kelet-ai/python-sdk)
- [TypeScript SDK](https://github.com/Kelet-ai/typescript-sdk)

## License

MIT
