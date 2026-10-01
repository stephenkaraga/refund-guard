# ADR 0001: Measure the agent on τ²-bench

- Status: accepted
- Date: 2026-10-01

## Context

An agent that issues refunds has to be right every time, not on average. I need a way to measure reliability with a simulated customer, real tool calls, and a grader that checks outcomes rather than wording.

## Options

1. **Build my own harness.** Full control, but I'd spend weeks on a user simulator and grader, and nobody would trust numbers from a harness only I use.
2. **Use τ²-bench (Sierra, MIT).** Public, actively maintained, already has a user simulator, DB-state grading and the pass^k metric. Supports any LiteLLM model, including local ones.
3. **LLM-as-judge on transcripts only.** Cheap, but it grades how answers sound, not whether the money moved correctly.

## Decision

Use τ²-bench, pinned to release `v1.0.1`, and add a new `merchant_ops` domain from outside the package via its registry (no fork).

## Consequences

- Results are comparable with published τ²-bench numbers on other domains.
- Grading is mostly deterministic (DB end state); policy-refusal tasks also use NL assertions, which need an LLM judge and add some noise.
- Upgrading tau2 means re-checking the registry and runner APIs (they moved between `main` and `v1.0.1`).
- The domain could be contributed upstream later.
