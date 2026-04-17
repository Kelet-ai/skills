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

Spawn subagents manually (see past runs in `../kelet-integration-workspace/`). Each eval needs:

**With-skill agent prompt:**
```
Repo: <repo> branch: <repo_branch>
App context: <app_description>
Task: <prompt>
Skill: skills/kelet-integration/SKILL.md
Save outputs to: kelet-integration-workspace/iteration-N/<eval-name>/with_skill/outputs/
Save: transcript.md, changes.diff, questions_asked.md
```

**Baseline agent prompt:** same but no skill path, save to `without_skill/outputs/`.

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

## Viewing results

Use the skill-creator viewer:

```bash
cd ~/.claude/plugins/cache/claude-plugins-official/skill-creator/unknown/skills/skill-creator
python3 eval-viewer/generate_review.py \
  ../skills/kelet-integration-workspace/iteration-N \
  --skill-name "kelet-integration" \
  --benchmark ../skills/kelet-integration-workspace/iteration-N/benchmark.json \
  --static /tmp/kelet-eval-review.html
open /tmp/kelet-eval-review.html
```
