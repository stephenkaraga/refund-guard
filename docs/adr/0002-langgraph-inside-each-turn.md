# ADR 0002: Use LangGraph inside each turn, not around the whole conversation

- Status: accepted
- Date: 2026-10-01

## Context

τ²-bench drives the conversation: it calls the agent once per turn and executes tool calls itself. A LangGraph app that owns the whole loop (calling tools directly) wouldn't fit the harness.

## Decision

Each `generate_next_message` call runs a small compiled LangGraph graph: `draft → check → (done | revise | fallback)`. The graph decides *what to send this turn*; τ²-bench still owns the conversation and tool execution.

## Consequences

- The agent plugs into τ²-bench unchanged, and the same class runs in production (see `deploy/agentcore`).
- The graph is where reliability features go: the guard today; retrieval, planning or a self-check node later.
- Baseline and guarded agents share the graph and prompt; the baseline just skips `check`. Differences in results come from the guard alone.
- Each blocked draft costs one more LLM call; this cost is reported per task.
