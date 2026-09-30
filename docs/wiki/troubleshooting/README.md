# Troubleshooting

When something does not work, look at **where you saw the problem**:

| Where you saw it | What it is | Page |
|---|---|---|
| A red list after pressing **Import**, or a message above a table after adding, changing or deleting a row | An **import or editing error**: a cell, code or value the data rules refuse. Nothing was changed | [Import and editing errors](import-errors.md) |
| On the **Pre-flight** tab (red for errors, amber for warnings), or **Start** is disabled | A **pre-flight issue**: the data would make a timetable impossible or pointless | [Pre-flight issues](preflight-issues.md) |
| The status of a run is not `succeeded`, or the **Why it did not finish** list on the Run tab | A **run status** and its messages | [Run statuses and messages](run-statuses.md) |
| A run is `infeasible` | No timetable exists: a set of hard rules collide | [Infeasible runs](infeasible.md) |

## Three layers of checking

The program checks your data three times, each one stricter and slower than the one before:

1. **Import and editing** reads every cell. It catches typing mistakes: a number that is not a number, a code that does not exist, a column with the wrong name. It is all or nothing, so a file with any mistake changes nothing.
2. **Pre-flight** looks at the meaning of the data without solving. It catches things that cannot work: a room that is too small for anything, a teacher with more hours than periods, a constraint with settings it cannot use. It takes a fraction of a second.
3. **The run** solves. It can still find that a *combination* of rules cannot hold together (`infeasible`), or run out of time.

Because of this order, fixing the first layer's messages often makes the next layer's disappear.

## Tips that save time

- **Fix the first message first.** One mistake often causes several messages.
- **Codes are case-sensitive.** `Lab-1` is not `lab-1`. Most `unknown code` messages are spelling.
- **Change one thing, then check again.** Especially with `infeasible` runs.
- **Use the links.** A pre-flight message links to the row to fix.
- **Look at the score breakdown** when a run succeeds but is not as good as you hoped.

## Related

- [Basics](../basics.md)
- [Tables](../tables/README.md)
- [Constraints](../constraints/README.md)
