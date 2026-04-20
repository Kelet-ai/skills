#!/usr/bin/env python3
"""Convert a workspace/iteration-N/ directory into the viewer-shaped benchmark JSON.

The checked-in benchmark.json files use a compact shape that is easy to eyeball in a
PR diff but that the skill-creator eval viewer doesn't render. This script pivots the
per-run grading.json files plus the compact benchmark.json into the shape the viewer
expects, and writes it to stdout.

Usage:
    python3 evals/build_viewer_benchmark.py workspace/iteration-N > /tmp/iter-N.json
    python3 .../generate_review.py workspace/iteration-N \\
        --benchmark /tmp/iter-N.json --static /tmp/review.html
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVALS_JSON = REPO_ROOT / "evals" / "evals.json"


def load_eval_ids() -> dict[str, int]:
    data = json.loads(EVALS_JSON.read_text())
    return {e["name"]: e["id"] for e in data["evals"]}


def build(iteration_dir: Path) -> dict:
    eval_ids = load_eval_ids()
    compact_path = iteration_dir / "benchmark.json"
    compact = json.loads(compact_path.read_text()) if compact_path.exists() else {}

    runs = []
    for eval_dir in sorted(iteration_dir.iterdir()):
        if not eval_dir.is_dir():
            continue
        for config_dir in sorted(eval_dir.iterdir()):
            if not config_dir.is_dir():
                continue
            grading_path = config_dir / "grading.json"
            if not grading_path.exists():
                continue
            g = json.loads(grading_path.read_text())
            runs.append({
                "run_id": g["run_id"],
                "eval_id": eval_ids.get(eval_dir.name),
                "eval_name": eval_dir.name,
                "configuration": g.get("config", config_dir.name),
                "run_number": 1,
                "result": g["summary"],
                "expectations": g["expectations"],
            })

    run_summary: dict[str, dict] = {}
    for config in {r["configuration"] for r in runs}:
        rates = [r["result"]["pass_rate"] for r in runs if r["configuration"] == config]
        run_summary[config] = {
            "pass_rate": {
                "mean": statistics.mean(rates) if rates else 0,
                "stddev": statistics.stdev(rates) if len(rates) > 1 else 0.0,
            }
        }

    metadata = dict(compact.get("metadata") or {})
    metadata.setdefault("skill_name", compact.get("skill_name", "kelet-integration"))
    metadata.setdefault("runs_per_configuration", 1)
    metadata.setdefault("evals_run", sorted({r["eval_id"] for r in runs if r["eval_id"]}))

    return {
        "skill_name": compact.get("skill_name", "kelet-integration"),
        "metadata": metadata,
        "run_summary": run_summary,
        "runs": runs,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("iteration", type=Path, help="workspace/iteration-N directory")
    args = ap.parse_args()

    if not args.iteration.is_dir():
        sys.exit(f"not a directory: {args.iteration}")

    json.dump(build(args.iteration), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
