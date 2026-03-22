# CLAUDE.md

This repo contains [Agent Skills](https://agentskills.io/specification) for the Kelet platform.

## Repo Structure

```
skills/
└── <skill-name>/
    ├── SKILL.md          # Required: frontmatter + instructions
    └── references/       # Optional: reference files loaded on demand
        ├── api.md
        └── signals.md
```

Each skill is a self-contained directory under `skills/`. The directory name must match the `name` field in `SKILL.md`.

## Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with valid frontmatter (`name`, `description`, `license`, `metadata`)
2. Add reference files under `skills/<skill-name>/references/` if the skill needs supplemental detail
3. Validate: `skills-ref validate ./skills/<skill-name>` (install: `npm i -g skills-ref`)

## Skill Writing Conventions

**Skills teach concepts and nuance — not code.** Claude already knows Python, TypeScript, React, etc. Only include what Claude genuinely doesn't know:
- New workflows or interactive processes
- Non-obvious API differences (e.g. TS `agenticSession` is callback-based, not a context manager)
- Silent failure modes
- Conceptual rules (e.g. what makes an "agentic flow", secret vs publishable key)

**Keep `SKILL.md` under 300 lines.** Move supplemental detail to `references/` files — Claude loads them on demand.

**Reference the spec:** https://agentskills.io/specification
**Reference best practices:** https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

## Kelet-Specific Rules

- **Synthetic signals = platform responsibility.** Never generate `source=SYNTHETIC` in customer code by default. Instead, generate a deeplink after Phase 0c: base64url-encode `{"use_case": "<description from 0b>", "ideas": [...]}` and present `https://console.kelet.ai/synthetics/setup?deeplink=<encoded>` — the console generates tailored evaluator configs for the developer to review and activate.
- **Two API key types:** secret (`KELET_API_KEY`, server-only) and publishable (`VITE_KELET_PUBLISHABLE_KEY`, frontend-safe). Never mix them.
- **Package names:** `kelet` (Python + TypeScript), `@kelet-ai/feedback-ui` (React).
