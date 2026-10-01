# ADR 0004: Iterate on local models, report on hosted models

- Status: accepted
- Date: 2026-10-01

## Context

Each eval run is (tasks × trials × turns) LLM calls for the agent *and* the user simulator. Paying for every iteration adds up, but a weak user simulator makes mistakes that get blamed on the agent.

## Decision

- Develop and debug against a quantized local model (Ollama via LiteLLM).
- Report headline numbers with a strong hosted model for the **user simulator**, and show the agent on both a local and a hosted model.
- Always report cost per task next to pass^k.

## Consequences

- Most iteration is free; reported runs cost a few dollars.
- The results table answers a real architecture question: how much reliability does the bigger model buy, and does the guard close the gap for the cheaper one?
