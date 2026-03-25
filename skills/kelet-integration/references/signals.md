# Kelet Signals Reference

## Signal Kinds

| Kind | Use when |
|---|---|
| `FEEDBACK` | User explicitly rates quality (thumbs up/down, star rating) |
| `EDIT` | User modifies AI-generated content — implicit "this was wrong" |
| `EVENT` | A notable action occurred (retry clicked, flow abandoned, feature used) |
| `METRIC` | A numeric quality measurement (score 0.0–1.0) |
| `ARBITRARY` | Custom/untyped observation that doesn't fit above |

## Signal Sources

| Source | Use when |
|---|---|
| `HUMAN` | Signal came from a real user action |
| `LABEL` | Signal came from a human labeling/review process |
| `SYNTHETIC` | Automated signal — **see platform note below** |

## Synthetic Signals: Platform vs Code

**Synthetic signals are Kelet's responsibility, not the developer's.**

For LLM-as-judge evaluators, heuristic checks, quality monitors:
→ Direct the developer to `https://console.kelet.ai/synthetics`
Kelet manages evaluators there on their behalf — no code required, cold-start solution included.

Only write `source=SYNTHETIC` signal code if:
1. Developer explicitly requests it, AND
2. The platform genuinely cannot implement it (explain why, ask developer to confirm)

## Signal Brainstorming: 3–5 per flow

Cap proposals at 5 per agentic flow. Prioritize by signal-to-noise:
- **Highest value**: edit signals (user directly shows what was wrong) and explicit downvotes
- **High value**: abandonment / retry events (strong implicit dissatisfaction signal)
- **Medium value**: tool call failures, API errors (automated, low noise)
- **Lower value**: generic page events (high noise, less specific to agent quality)

For each proposal, state: what it captures → how it manifests → what failure it reveals to Kelet's RCA engine.

## Required Fields

- `kind` (required)
- `source` (required)
- `session_id` OR `trace_id` (at least one required — auto-resolved from `agentic_session` context if not passed explicitly)
- `trigger_name` (optional) — identifies what the signal represents; see naming conventions below
- `score` (0.0–1.0 if provided)
- `value` (optional) — text content: feedback text, edit diff, reasoning, etc.
- `confidence` (0.0–1.0 if provided)
- `metadata` (optional) — arbitrary dict for extra context

---

## Naming Conventions

Use `trigger_name` to identify what a signal represents. Follow `source-action` format: lowercase, hyphenated, two-part names that reflect where the signal came from and what happened.

| Good | Bad | Why |
|---|---|---|
| `user-vote` | `good-response` | Name the source+action, not the assumed quality |
| `user-edit` | `edit` | Include source to distinguish from system edits |
| `user-retry` | `retry_button_clicked` | Concise; no UI implementation details |
| `system-timeout` | `timeout_error_occurred` | Describe the signal, not the error log |

**Rules:**
- Don't encode assumed quality: `user-thumbs-down`, not `bad-response`
- Consistent across flows — Kelet clusters by `trigger_name`; inconsistent names fragment analytics
- Same behavior in different projects → same name
