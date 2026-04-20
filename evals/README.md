# Evals

Evaluates the `kelet-integration` skill against real codebases.

## Schema (`evals.json`)

```json
{
  "skill_name": "kelet-integration",
  "evals": [
    {
      "id": 1,
      "name": "short-slug",
      "prompt": "what the developer types",
      "app_description": "context prepended to the prompt — describes the app so the agent knows the stack",
      "repo": "../some-repo",
      "repo_branch": "branch-to-check-out",
      "expected_output": "human-readable description of success",
      "assertions": [
        {
          "id": "snake_case_id",
          "description": "what to check",
          "type": "code | llm"
        }
      ]
    }
  ]
}
```

**Fields:**
- `repo` + `repo_branch` — the agent checks out this branch before running. The branch should represent the pre-integration state of the app.
- `app_description` — prepended to `prompt` as context. Describes stack, session model, frontend, deployment.
- `assertions[].type` — `code` = checkable by grepping `changes.diff`; `llm` = requires reading transcript/outputs.

## Why not use skill-creator's runner?

The skill-creator runner fires a prompt and checks outputs. Our evals also require:
1. A real codebase checked out to a specific branch
2. The agent to actually edit files in that repo
3. Grading against the resulting `git diff`

The skill-creator viewer and grading schema (`grading.json` with `expectations[].text/passed/evidence`) are compatible and reusable. The runner is not.

## Running evals

Spawn subagents manually (see past runs in `workspace/`). Each eval needs:

**With-skill agent prompt:**
```
Repo: <repo> branch: <repo_branch>
App context: <app_description>
Task: <prompt>
Skill: skills/kelet-integration/SKILL.md
Save outputs to: evals/workspace/iteration-N/<eval-name>/with_skill/outputs/
Save: transcript.md, changes.diff, questions_asked.md
```

**Baseline agent prompt:** same but no skill path, save to `without_skill/outputs/`.

## Running with the stub server

Skill v1.4.0+ makes the skill `curl` `api.kelet.ai` at Checkpoint 2 to auto-create
synthetic evaluators. Evals don't have real credentials, so we substitute in a
local stub that mirrors the production response contract.

1. **Start the stub** (port 8765):

   ```bash
   python3 evals/dummy_server.py &
   ```

2. **Run evals sequentially** — the stub binds a single port, so don't spawn
   parallel subagents against it. Run #1 → #4 → #6 → #7 → #8 back-to-back.

3. **Subagent prompt injection** — append this verbatim to every with-skill
   prompt that could reach Checkpoint 2:

   > **Eval environment note:** the real Kelet API is not reachable. When the
   > skill tells you to `curl https://api.kelet.ai/...`, substitute
   > `http://localhost:8765/...`. Any token `sk-kelet-*` is accepted by the
   > stub; `sk-typo-wrong` and other non-`sk-kelet-*` keys will return 401.
   > The project name `not-a-real-project` returns 404 with a hint. Record the
   > curl invocation and response verbatim in `transcript.md`. This is an eval
   > harness override — do NOT modify `SKILL.md` or `signals.md`.

4. **Teardown:** `kill %1` (or `pkill -f dummy_server.py`).

Contract source for the stub: `kelet/server/app/routers/synthetics.py` and
`kelet/server/tests/test_synthetics_endpoint.py`. Keep them in sync.

## Grading

Write `grading.json` to each run directory (NOT inside `outputs/`):

```json
{
  "run_id": "<eval-name>-<config>",
  "eval_name": "<eval-name>",
  "config": "with_skill | without_skill",
  "summary": { "passed": 7, "failed": 1, "total": 8, "pass_rate": 0.875 },
  "expectations": [
    { "id": "...", "text": "...", "passed": true, "evidence": "..." }
  ]
}
```

## Workspace = regression baselines

Each `workspace/iteration-N/` dir is a **frozen snapshot** of one full eval sweep —
the grading and benchmark at that point in time. These are the regression baselines:
the next iteration's numbers are compared against them to detect drift when the SKILL
changes. **After every full sweep, commit the iteration dir (including `benchmark.json`
and all `<eval>/<config>/grading.json` files) to the PR** so the baseline moves with
the skill.

Implications:
- They are **not** re-executed when `evals.json` changes. Adding a new assertion does
  not retroactively fail a saved iteration — the baseline represents the skill's
  behavior against the assertion set at the time of the run.
- Each fresh eval run is a new agent invocation over `../docs-ai@<repo_branch>` (the
  pre-integration state defined in `evals.json`), graded against the current assertion
  list.

## Viewing results

The checked-in `benchmark.json` uses a compact shape (good for PR diffs) that the
skill-creator viewer doesn't render — convert it with `build_viewer_benchmark.py`
first. The converter walks each `<eval>/<config>/grading.json` under the iteration
directory and emits the viewer's expected shape (`run_summary: {<config>: {pass_rate:
{mean, stddev}}}`, `runs[].{eval_id, run_number, result, expectations}`).

```bash
# 1. Build viewer-shaped benchmark from the per-run grading.json files
python3 evals/build_viewer_benchmark.py evals/workspace/iteration-N > /tmp/iter-N.json

# 2. Generate the HTML
python3 ~/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator/eval-viewer/generate_review.py \
  evals/workspace/iteration-N \
  --skill-name "kelet-integration" \
  --benchmark /tmp/iter-N.json \
  --static /tmp/kelet-eval-review.html
open /tmp/kelet-eval-review.html
```
