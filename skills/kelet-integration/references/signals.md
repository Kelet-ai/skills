# Kelet Signals Reference

## Contents

- [Signal Enums + Required Fields](#signal-enums--required-fields)
- [Selecting Synthetic Evaluators](#selecting-synthetic-evaluators) — preset list
- [Synthetic Deeplink Generation](#synthetic-deeplink-generation)
- [Naming Conventions](#naming-conventions)

---

## Signal Enums + Required Fields

`kind`: `FEEDBACK` (explicit rating) · `EDIT` (user modifies AI output) · `EVENT` (retry, abandon, copy) · `METRIC` (numeric score) · `ARBITRARY` (custom)

`source`: `HUMAN` (user action) · `LABEL` (human review process) · `SYNTHETIC` (automated — platform responsibility)

Required: `kind`, `source`, and at least one of `session_id` or `trace_id` (auto-resolved from `agentic_session` context). `score` must be 0.0–1.0 if provided.

## Synthetic Signals: Platform vs Code

Kelet already has the full trace: every LLM call, model response, tool invocations, latency, token counts, turn structure. That's enough information to evaluate most quality dimensions (task completion, relevance, faithfulness, hallucination, sentiment) without the developer writing a single line. Synthetic evaluators run on the platform against this trace data — no code, no deployment, cold-start included.

**Default assumption: if Kelet can see it in the trace, it's a managed synthetic.** Only propose coded `source=SYNTHETIC` signals for information Kelet can't observe — e.g. a score from an external system, a domain-specific classifier running outside the LLM path, or a ground-truth comparison against a private dataset.

Direct developers to `https://console.kelet.ai/<project>/synthetics` — Kelet manages evaluators there.

Only write `source=SYNTHETIC` code if: (1) developer explicitly requests it AND (2) platform genuinely cannot implement it — explain why and ask developer to confirm.

## Signal Priority (highest diagnostic value first)

1. Edit signals — user directly shows what was wrong
2. Explicit downvotes
3. Abandonment / retry — strong implicit dissatisfaction
4. Tool call failures, API errors — automated, low noise
5. Generic page events — high noise, least specific

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

## Synthetic Creation

Two paths. Primary (auto-create via API) whenever the user pastes `KELET_API_KEY`. Fallback (deeplink) only when the user explicitly declines to paste a secret.

### Primary: API call

The server creates, upserts, and dedups evaluators in one call. **Long-running — 1–3 minutes typical, up to 5.** Print the "sit tight" banner (see SKILL.md § Checkpoint 2) before running the curl.

**MUST EXECUTE this with the Bash tool** (set `timeout: 400000`) — never show as a code block for the user to copy:

```bash
curl -sS --max-time 360 \
  -X POST "https://api.kelet.ai/api/projects/<project>/synthetics" \
  -H "Authorization: Bearer $KELET_API_KEY" \
  -H 'Content-Type: application/json' \
  -w '\n%{http_code}\n' \
  -d '{"use_case":"<use_case>","ideas":[{"id":"<id>","name":"<name>","description":"<desc>","evaluator_type":"llm"}]}'
```

⚠️ Do NOT add `-f` / `--fail` — that flag makes curl drop the response body on 4xx/5xx, which breaks `project_not_found` hint surfacing and 401 diagnosis.

The `-w '\n%{http_code}\n'` appends the HTTP status on its own final line after the response body. Split them when parsing: last line = status code, everything before = body.

Include only evaluators the developer selected. Idea fields mirror the server's `SignalIdea`:
- `id` (required) — short slug (e.g. `task-completion`)
- `name` (required) — display name
- `description` (required) — what it measures
- `evaluator_type` (required) — `"llm"` for semantic/qualitative, `"code"` for deterministic (`len()`, regex, JSON-parse)
- `icon` (optional) — console icon key
- `context` (optional) — steers the generator toward something specific to this use case

**Response parsing.** Body is plain text: `created=N updated=N failed=N deduped=bool`.
- `failed > 0` → warn: "N ideas timed out — re-run the skill to retry those."
- HTTP 200 → success; 401 → invalid key; 404 with `project_not_found` → surface the server's hint; 504 / connection timeout → "Generator was slow. Re-run to retry — partial state was persisted."; 5xx / network → fail loud.

### Fallback: deeplink

**Only use when the user declines to paste a secret key.** No project verification possible.

Base64url-encode the payload, then build a markdown link so the terminal renders it as a clickable label:

```python
python3 -c \
"import base64,json; project='<project>'; payload={'use_case':'<use_case>','ideas':[{'name':'<name>','evaluator_type':'llm','description':'<desc>'}]}; url=f'https://console.kelet.ai/{project}/synthetics/setup?deeplink='+base64.urlsafe_b64encode(json.dumps(payload,separators=(',',':')).encode()).rstrip(b'=').decode(); print(f'[Open Kelet synthetic setup → {project}]({url})')"
```

Present the markdown link as a bold action item. Add a note: "I can't verify the project name without a key — make sure it matches what you created in the console."

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
