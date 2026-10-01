"""Command line entry points.

merchant-ops tasks                       # list tasks and splits
merchant-ops run --agent guarded ...     # run an eval and save results
merchant-ops compare a.json b.json       # pass^k side by side
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help="Merchant ops agent evals on tau2-bench.")

AGENTS = {"baseline": "mo_baseline", "guarded": "mo_guarded"}
RESULTS_DIR = Path("results")


@app.command()
def tasks(split: str | None = typer.Option(None, help="Only show this split")) -> None:
    """List tasks (and which splits they belong to)."""
    from merchant_ops.domain.environment import get_tasks, get_tasks_split

    splits = get_tasks_split()
    for t in get_tasks(split):
        member_of = [name for name, ids in splits.items() if t.id in ids]
        typer.echo(f"{t.id:36} {', '.join(member_of)}")


@app.command()
def run(
    agent: str = typer.Option("guarded", help="baseline or guarded"),
    llm: str = typer.Option("anthropic/claude-sonnet-5-5", help="Agent model (LiteLLM id)"),
    user_llm: str = typer.Option("anthropic/claude-sonnet-5-5", help="User-simulator model"),
    judge_llm: str | None = typer.Option(
        None, help="Model that grades NL assertions (policy tasks). Defaults to --user-llm."
    ),
    split: str = typer.Option("base", help="Task split"),
    trials: int = typer.Option(4, help="Trials per task; pass^k uses k <= trials"),
    task_id: list[str] | None = typer.Option(None, help="Run only these task IDs"),
    concurrency: int = typer.Option(4, help="Concurrent simulations"),
    seed: int = typer.Option(42),
) -> None:
    """Run one agent on the merchant_ops domain and save the results."""
    from tau2.data_model.simulation import TextRunConfig
    from tau2.metrics.agent_metrics import compute_metrics
    from tau2.runner import run_domain

    from merchant_ops.register import register, set_judge_llm

    if agent not in AGENTS:
        raise typer.BadParameter(f"agent must be one of {list(AGENTS)}")
    from tau2.utils.utils import DATA_DIR

    register()
    set_judge_llm(judge_llm or user_llm)
    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_name = f"merchant_ops_{stamp}_{agent}_{llm.replace('/', '_').replace(':', '_')}"
    # tau2 writes to <TAU2_DATA_DIR>/simulations/<run_name>/results.json;
    # we copy it into ./results so everything for this repo lives in one place.
    tau2_results = DATA_DIR / "simulations" / run_name / "results.json"
    save_to = RESULTS_DIR / f"{run_name}.json"

    config = TextRunConfig(
        domain="merchant_ops",
        agent=AGENTS[agent],
        llm_agent=llm,
        llm_user=user_llm,
        task_split_name=split,
        task_ids=task_id or None,
        num_trials=trials,
        max_concurrency=concurrency,
        save_to=run_name,
        seed=seed,
    )
    results = run_domain(config)
    if tau2_results.exists():
        shutil.copyfile(tau2_results, save_to)
    else:
        save_to.write_text(results.model_dump_json(indent=2))
    metrics = compute_metrics(results)
    summary = {
        "agent": agent,
        "llm": llm,
        "split": split,
        "trials": trials,
        "avg_reward": metrics.avg_reward,
        "pass_hat_k": metrics.pass_hat_ks,
        "avg_agent_cost_usd": metrics.avg_agent_cost,
        "results_file": str(save_to),
    }
    summary_path = save_to.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    typer.echo(json.dumps(summary, indent=2, default=str))


@app.command()
def compare(summaries: list[Path]) -> None:
    """Print pass^k, reward and cost for several *.summary.json files."""
    rows = [json.loads(p.read_text()) for p in summaries]
    ks = sorted({int(k) for r in rows for k in r["pass_hat_k"]})
    header = ["agent", "llm", "avg_reward", "cost_usd"] + [f"pass^{k}" for k in ks]
    typer.echo(" | ".join(header))
    for r in rows:
        cells = [r["agent"], r["llm"], f"{r['avg_reward']:.3f}", f"{r['avg_agent_cost_usd']:.4f}"]
        cells += [f"{r['pass_hat_k'].get(str(k), r['pass_hat_k'].get(k, 0)):.3f}" for k in ks]
        typer.echo(" | ".join(cells))


if __name__ == "__main__":
    app()
