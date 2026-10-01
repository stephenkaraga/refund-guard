# Architecture

## Evaluation loop

```mermaid
sequenceDiagram
    participant U as tau2 user simulator
    participant O as tau2 orchestrator
    participant A as MerchantOpsAgent (LangGraph)
    participant G as Guard
    participant T as merchant_ops tools (mock DB)
    participant E as tau2 evaluator

    U->>O: merchant message
    O->>A: generate_next_message(message, state)
    A->>A: draft (LLM call)
    A->>G: proposed write call + evidence from history
    alt blocked
        G-->>A: violations
        A->>A: redraft with feedback (max 2), else fallback
    end
    A-->>O: reply or tool call
    O->>T: execute tool call
    T-->>O: result
    O->>A: tool result (next turn)
    Note over O,E: conversation ends
    O->>E: final DB + transcript
    E-->>O: reward (DB match x NL assertions)
```

## Components

| Component | File | Responsibility |
| --- | --- | --- |
| Domain data model | `src/merchant_ops/domain/data_model.py` | Merchants, transactions, disputes, payouts |
| Tools | `src/merchant_ops/domain/tools.py` | Lookups and two write actions; hard limits only |
| Policy | `data/merchant_ops/policy.md` | Business rules the agent must follow |
| Tasks | `data/merchant_ops/tasks.json` | Scenarios + expected end state / assertions |
| Agent | `src/merchant_ops/agent/graph_agent.py` | LangGraph turn graph, baseline and guarded variants |
| Evidence | `src/merchant_ops/agent/evidence.py` | Facts the agent has seen, parsed from tool results |
| Guard | `src/merchant_ops/agent/guard.py` | Deterministic write-action rules |
| Registration | `src/merchant_ops/register.py` | Plugs domain and agents into tau2 without a fork |

## Trust boundaries

- The model proposes; the guard disposes. No write call reaches the tools without passing the guard (guarded agent).
- The guard trusts only tool results, never the model's or the user's claims about facts.
- Production adds a second boundary at the gateway (see `deploy/agentcore/README.md`).

## Scoring

- **DB tasks:** reward 1 if the final DB matches replaying the reference actions on a fresh DB.
- **Policy tasks:** DB must be unchanged (or match) **and** every NL assertion must be judged true.
- **pass^k:** probability that all k trials of a task succeed; reported for k = 1, 2, 4.
