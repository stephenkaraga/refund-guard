# Failure taxonomy

Label every failed simulation with **one primary category** (and optional secondary). Counts per category drive what to fix next.

| Code | Category | Example | Usually fixed by |
| --- | --- | --- | --- |
| `POLICY_WRITE` | Took a write action the policy forbids | Refunded a charge under open dispute | Guard rule |
| `POLICY_SPEECH` | Said something the policy forbids | Revealed the risk score | Prompt, output check |
| `MISSED_ACTION` | Should have acted, didn't | Never issued the allowed refund | Prompt, planning node |
| `WRONG_ARGS` | Right tool, wrong arguments | Refunded $120 instead of $100; wrong reason | Lookup-before-act, guard |
| `WRONG_TOOL` | Wrong tool or wrong order | Transferred when it could have refunded | Prompt, examples |
| `NO_LOOKUP` | Acted on assumed facts | Refunded without fetching the transaction | Evidence rule |
| `AUTH` | Skipped or botched authentication | Acted before verifying email | Guard rule |
| `CONFIRM` | Acted without explicit yes, or guard blocked a real yes | — | Guard regex tuning |
| `OVER_REFUSAL` | Refused something allowed | Refused a valid partial refund | Loosen rule or prompt |
| `USER_SIM` | User simulator went off-script | Simulator invented a transaction ID | Task wording; not the agent's fault |
| `TASK_BUG` | Task or expected outcome is wrong | Reference action violates policy | Fix the task |
| `INFRA` | Timeout, API error | — | Re-run |

## Process

1. Run `python evals/label_failures.py results/<file>.json` to export failed sims to a CSV.
2. Read each transcript; fill `primary`, `secondary`, `notes`.
3. Count by `primary`. The biggest agent-side bucket is the next fix.
4. Exclude `USER_SIM`, `TASK_BUG` and `INFRA` from the agent's score in the write-up, and say how many there were.
