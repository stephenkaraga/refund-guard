"""Export failed simulations from a tau2 results file to a CSV for labeling.

    python evals/label_failures.py results/<run>.json [-o failures.csv]

Columns: task_id, trial, reward, termination, last_agent_message, primary,
secondary, notes. Fill the last three by hand using evals/failure_taxonomy.md.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def _last_agent_text(messages: list[dict]) -> str:
    for m in reversed(messages or []):
        if m.get("role") == "assistant" and m.get("content"):
            return str(m["content"])[:300]
    return ""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    p.add_argument("-o", "--out", type=Path, default=None)
    args = p.parse_args()

    data = json.loads(args.results.read_text())
    sims = data.get("simulations", [])
    out = args.out or args.results.with_suffix(".failures.csv")

    rows = []
    for s in sims:
        reward = (s.get("reward_info") or {}).get("reward")
        if reward is not None and reward >= 1.0:
            continue
        rows.append(
            {
                "task_id": s.get("task_id"),
                "trial": s.get("trial"),
                "reward": reward,
                "termination": s.get("termination_reason"),
                "last_agent_message": _last_agent_text(s.get("messages", [])),
                "primary": "",
                "secondary": "",
                "notes": "",
            }
        )

    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["task_id"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} failed of {len(sims)} simulations -> {out}")


if __name__ == "__main__":
    main()
