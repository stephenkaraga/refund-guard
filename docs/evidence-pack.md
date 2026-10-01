# Evidence pack (one-page story template)

Fill this in after the runs. Keep it to one page.

## Problem

Agents that can move money must follow policy every time. How reliable is a tool-using LLM agent at merchant payment support, and what makes it more reliable?

## Approach

- New `merchant_ops` domain for τ²-bench: policy, tools, N tasks (M adversarial).
- LangGraph agent; baseline vs. deterministic guard on write actions.
- Models: _local model_ and _hosted model_; 4 trials per task.

## Results

| Agent | Model | pass^1 | pass^4 | cost / task |
| --- | --- | --- | --- | --- |
| baseline | | | | |
| guarded | | | | |

One sentence: what changed and by how much.

## What broke

Top three failure categories with counts and one short example each (from `evals/failure_taxonomy.md`).

## What I'd do in production

Two or three sentences pointing to `deploy/agentcore/README.md`: identity-based auth, Cedar rules at the gateway, nightly evals.

## Links

Repo · demo video · upstream PR
