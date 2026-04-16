# Kelet Signals Reference

## Contents

- [Signal Enums + Required Fields](#signal-enums--required-fields)
- [Selecting Synthetic Evaluators](#selecting-synthetic-evaluators) — preset list
- [Synthetic Deeplink Generation](#synthetic-deeplink-generation)
- [Naming Conventions](#naming-conventions)

---

## Signal Enums + Required Fields

`kind`: `FEEDBACK` (explicit rating) · `EDIT` (user modifies AI output) · `EVENT` (retry, abandon, copy) · `METRIC` (numeric score) · `ARBITRARY` (custom)

`source`: `HUMAN` (user action) · `LABEL` (human review process) · `SYNTHETIC` (automated — platform responsibility, see SKILL.md)

Required: `kind`, `source`, and at least one of `session_id` or `trace_id` (auto-resolved from `agentic_session` context). `score` must be 0.0–1.0 if provided.

---

## Selecting Synthetic Evaluators

**Core selection framework:**

1. **One per failure category, no overlap.** Every agent fails in a finite set of ways. Map each failure mode
   from the signal analysis pass to a category, then pick ONE evaluator per category. Two evaluators on the same category
   (e.g. `Completeness` + `Relevance` + `Answer Relevancy`) multiply noise without adding information.

   | Category | What it measures | When it matters |
   |----------|-----------------|-----------------|
   | Comprehension | Did it understand what was asked? | Always |
   | Execution | Did it take the right actions? (retrieval, tool choice) | RAG, multi-tool |
   | Correctness | Is the output factually right? | RAG, knowledge agents |
   | Usefulness | Is the output actionable and complete? | Always |
   | Behavior | Was the interaction appropriate? | Customer-facing, role-based |
   | User reaction | Implicit signal from the user's next action | Always (if multi-turn) |

2. **Captures what traces can't.** Traces already record latency, tokens, tool calls, errors. Evaluators
   should measure what's invisible in the trace: semantic quality, faithfulness to context, user satisfaction.

3. **Grounded in the agent's actual behavior.** `RAG Faithfulness` is useless without a retrieval step.
   `Tool Usage Efficiency` is useless without tool calls. Match the evaluator to what the agent actually does.

4. **Type is determined by the check, not the concept.** If understanding content is required to make the
   judgment, it's `llm` — even if the concept sounds simple. `code` is ONLY for checks a junior dev could
   write in one line without reading the content (`len()`, `json.parse()`, regex, field presence).

**Prefer platform presets** — the Kelet console has built-in evaluators for common patterns. Use the exact
preset name in the deeplink; the platform auto-configures them. Custom evaluators only when no preset fits.

**Universal — apply to almost any agent:**

| Preset Name                 | Type | Catches                                                                        |
|-----------------------------|------|--------------------------------------------------------------------------------|
| `Task Completion`           | llm  | Did the agent accomplish the user's goal?                                      |
| `Conversation Completeness` | llm  | User intentions left unaddressed or deflected                                  |
| `Answer Relevancy`          | llm  | Off-topic responses, padding, missed the actual question                       |
| `Sentiment Analysis`        | llm  | User frustration, dissatisfaction, repeated corrections throughout the session |
| `Session Health Stats`      | code | Turn counts, token usage, tool frequency — structural anomalies                |

**RAG / retrieval agents:**

| Preset Name               | Type | Catches                                                                   |
|---------------------------|------|---------------------------------------------------------------------------|
| `RAG Faithfulness`        | llm  | Claims contradicting retrieved documents — context-specific hallucination |
| `Hallucination Detection` | llm  | Fabricated facts, non-existent citations (no retrieval context required)  |

**Multi-tool / agentic:**

| Preset Name             | Type | Catches                                                      |
|-------------------------|------|--------------------------------------------------------------|
| `Loop Detection`        | code | Repeated tool calls, circular execution patterns             |
| `Tool Usage Efficiency` | llm  | Redundant calls, retry loops, poor sequencing                |
| `Knowledge Retention`   | llm  | Agent forgets facts the user provided earlier in the session |

**Role / behavior:**

| Preset Name             | Type | Catches                                                             |
|-------------------------|------|---------------------------------------------------------------------|
| `Role Adherence`        | llm  | Agent drifts outside its assigned scope or persona                  |
| `Agent Over-Compliance` | llm  | Sycophancy — changing answer when user pushes back without new info |

⚠️ Type trap: "did the agent refuse when it should have helped?" sounds binary but requires understanding intent
→ always `llm`. Only use `code` if a junior dev could write the check in one line without reading the content.

---

## Synthetic Deeplink Generation

Base64url-encode the payload, then build `https://console.kelet.ai/<project>/synthetics/setup?deeplink=<encoded>` — substitute `<project>` with the project name confirmed in Checkpoint 2 (Batch 2).

**MUST EXECUTE this with the Bash tool** — never show as a code block for the user to copy:

```python
python3 -c \
"import base64,json; project='<project>'; payload={'use_case':'<use_case>','ideas':[{'name':'<name>','evaluator_type':'llm','description':'<desc>'}]}; print(f'https://console.kelet.ai/{project}/synthetics/setup?deeplink='+base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).rstrip(b'=').decode())"
```

Include only evaluators the developer selected. Add `"context"` to an idea only to steer the evaluator toward
something specific. `evaluator_type`: `"code"` = deterministic check; `"llm"` = semantic/qualitative.

---

## Naming Conventions

Use `trigger_name` to identify what a signal represents. Follow `source-action` format: lowercase, hyphenated, two-part
names that reflect where the signal came from and what happened.

| Good             | Bad                      | Why                                             |
|------------------|--------------------------|-------------------------------------------------|
| `user-vote`      | `good-response`          | Name the source+action, not the assumed quality |
| `user-edit`      | `edit`                   | Include source to distinguish from system edits |
| `user-retry`     | `retry_button_clicked`   | Concise; no UI implementation details           |
| `system-timeout` | `timeout_error_occurred` | Describe the signal, not the error log          |

Kelet clusters by `trigger_name` — inconsistent names fragment analytics. Same behavior across projects → same name.
