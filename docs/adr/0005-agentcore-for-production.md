# ADR 0005: Target Bedrock AgentCore for a production deployment

- Status: proposed
- Date: 2026-10-01

## Context

A benchmark agent isn't a product. A real deployment needs authenticated sessions, durable state, tool access over the real payments API with its own authorization, observability, and continuous evaluation.

## Options

1. **Self-host** (container + LangGraph checkpointer + API gateway + OpenTelemetry). Most control; most to build and operate.
2. **Bedrock AgentCore** (Runtime, Identity, Memory, Gateway, Policy, Observability, Evaluations). Managed pieces that map one-to-one onto the needs above; AWS lock-in.
3. **A vendor agent platform.** Fastest, least control over the guard and evals.

## Decision

Design for AgentCore (see `deploy/agentcore/README.md`), keeping the agent framework-neutral so option 1 stays open.

## Consequences

- Authentication moves from the conversation into Identity tokens.
- Write rules are enforced twice: the in-agent guard and Cedar rules at the Gateway.
- The τ²-bench task set becomes a regression suite in AgentCore Evaluations.
- Not built yet; the stub shows the contract and the gaps.
