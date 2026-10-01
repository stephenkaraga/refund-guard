# ADR 0003: Enforce write-action policy in code, not only in the prompt

- Status: proposed (to be confirmed by the failure analysis)
- Date: 2026-10-01

## Context

The policy is in the system prompt, but models still skip lookups, refund disputed charges, or exceed limits under user pressure. A prompt is a request; it isn't enforcement.

## Decision

Check every **write** tool call with a deterministic guard before it leaves the agent. The guard reads only facts the agent has seen in tool results this conversation (the "evidence") and blocks the call if:

| Rule | Blocks when |
| --- | --- |
| CONFIRM | the merchant's last message isn't an explicit yes |
| AUTH | no merchant has been authenticated |
| EVIDENCE | the transaction or its dispute hasn't been looked up |
| OWNERSHIP | the transaction belongs to another merchant |
| STATUS | the charge isn't settled |
| DISPUTE | a linked dispute is open or under review |
| WINDOW | the charge is older than 180 days |
| LIMIT | a single refund is over $500 |
| BALANCE | the amount exceeds the refundable balance |
| DEADLINE | dispute evidence is past due |

Blocked drafts go back to the model with the reasons (up to 2 retries), then a safe fallback reply.

## Consequences

- Rules are unit-tested and fast; the model can't argue past them.
- Evidence-based checks also catch hallucinated facts: no lookup, no refund.
- CONFIRM uses a regex and will have false negatives ("sure, why not"). Measure it; loosen or replace with a classifier if it costs pass rate.
- Some policy (business-name match, tone, not leaking the risk score) stays prompt-only. Those failures are tracked separately.
- In production the same rules belong in AgentCore Policy too (defense in depth).
