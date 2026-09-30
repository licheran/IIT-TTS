# Run statuses and messages

## What it's for

Every run ends in one status, shown on the [Run](../tabs/run.md) and [Runs](../tabs/runs.md) tabs. This page says what each one means, what the messages under **Why it did not finish** are, and what to do next.

## Statuses

| Status | What happened | What to do |
|---|---|---|
| `queued` | The run is waiting for a free worker | Wait. If it stays queued for a long time, the background worker may not be running: ask whoever runs the server |
| `running` | The solver is working | Wait, or press **Cancel** |
| `succeeded` | A timetable was found and checked by the independent verifier | Open it on the [Timetable](../tabs/timetable.md) tab. The score shows how well your soft rules are met |
| `infeasible` | No timetable can satisfy all the hard rules at once | Read **Why it did not finish**. See [Infeasible runs](infeasible.md) |
| `blocked` | [Pre-flight](preflight-issues.md) found errors, so the solver never started | Fix the errors listed on the Pre-flight tab |
| `cancelled partial` | You cancelled, and a timetable had already been found. The best one so far was kept | Use it, or start a longer run |
| `cancelled` | You cancelled before any timetable was found | Start again, with a longer time limit if needed |
| `invalid` | The solver's answer broke a hard rule when checked by the verifier. This should never happen | Report it, with the dataset. Do not use the timetable |
| `failed` | The run could not finish. See the message | See below |

## Messages under "Why it did not finish"

The Run tab lists the **errors** of a run under this heading. Warnings are kept with the run but are not shown there.

| Kind | Message | Meaning | What to do |
|---|---|---|---|
| `no_solution` | `no timetable found within 120 s (solver status: unknown)` | The time limit ended before a timetable was found. The data is not shown to be impossible | Start again with a **longer time limit** (for a big dataset, several minutes), or **more workers**. Use the mode `feasible` to stop at the first timetable. Pre-flight warnings such as `pooled_pressure` hint at tight data |
| `unsupported_constraint` | `hard constraint "X": type "…" is not supported by the solver yet` | A hard rule uses a type the solver cannot handle | Change the type, or make the rule soft |
| `solver_warning` (a warning, not listed on the Run tab) | `constraint "X" (…) is not supported by the solver yet and was ignored` | A soft rule was skipped | The run went on without it. Change the type if it matters |
| `solver_warning` (a warning, not listed on the Run tab) | `solved in two steps (…): times, then resources` | A large dataset was solved in two steps for speed | Nothing to do. It is information |
| `infeasible_reason` | A sentence from the solver | A reason found while the model was being built that already makes a timetable impossible | See [Infeasible runs](infeasible.md) |
| `infeasible_core` | `Conflicting rules: …` | The smallest set of rules that cannot hold together | See [Infeasible runs](infeasible.md) |
| `infeasible_unexplained` | `No timetable can satisfy every hard rule, but the conflicting rules could not be found in the time available. …` | The run is infeasible, but finding which rules collide took more time than the program allows | See [Infeasible runs](infeasible.md): make some hard constraints soft, one at a time |
| `violation` | A sentence naming the broken rule | The check found a problem in the timetable | For `invalid` runs, report it. For soft rules it is only information |
| a pre-flight kind | See [Pre-flight issues](preflight-issues.md) | The same messages you see on the Pre-flight tab, kept with the run | Fix them there |

A `failed` run can also end with `the worker stopped responding`, or an error name and text such as `ValueError: …`. These are faults of the system rather than of your data. The Run tab shows the text under **Why it did not finish**.

- `the worker stopped responding`: the background worker that was solving the run stopped and did not come back. The run is put back in the queue up to two more times before it is marked failed. Start it again. If this repeats, ask whoever runs the server to check the worker.
- `<ErrorName>: <text>`: an unexpected fault. Please report it with the dataset.

## The score and "best score"

A `succeeded` run shows a score (lower is better, `0` is perfect) and a breakdown of soft rules. A score that is not `0` does not mean anything is wrong: it means some preferences could not all be met. The [constraints overview](../constraints/README.md) explains how to read the breakdown.

While a run is going, **Best score** falls and **Bound** rises. They may never meet if the time limit is short: the timetable is then good, but not proven best.

## Related

- [Run](../tabs/run.md)
- [Runs](../tabs/runs.md)
- [Infeasible runs](infeasible.md)
