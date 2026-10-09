# ADR-0008: Teacher fairness rules are derived when a run is prepared

- **Status:** Accepted
- **Date:** 2026-10-09 (answers of the user to P25.1)

## Context
FR-20 asks for three things when the solver chooses teachers: a weekly cap per teacher, even sharing of the load among the teachers of a module, and the same teacher for a group. The catalogue (ADR-0005) gets three types for this: C15 `max_load`, C16 `balance_load` and C17 `same_resource`.

The academic preset needs one rule per module (the teachers of that module are balanced, a group keeps one teacher for each module and kind of session) and one cap per teacher. The preset's defaults (spec 04 §3) are seeded once, when a dataset is created, before it has any module or teacher. So per-module defaults cannot be seeded the way `AC-GAPS` is. Storing generated rows would also make the Constraints table grow with every module and go stale when a teacher's modules change.

## Options
1. **Seed rows into the Constraints table when a configuration is imported or edited.** The user sees and edits them. Rows go stale, and a change to `Teachers.modules` would need a rebuild of the generated rows with a rule for which rows the user owns.
2. **Add parameters that make one stored rule cover every module** (for example group by module). It puts a module-shaped idea into the generic types.
3. **Derive the rules when a run is prepared**, as demands are (ADR-0007). The preset's `derived_constraints(dataset)` returns them from the configuration; they are never stored. A row in the Constraints table with the same code wins, so a user can switch a derived rule off (`active=false`) or change its weight by adding a row with that code.

## Decision
Option 3. For a configured academic dataset:

| Code | Type | Scope | Params | Hard | Weight | Created for |
|---|---|---|---|---|---|---|
| `LOAD-<teacher>` | `max_load` | `code:<teacher>` | `{"max": <max_hours>, "unit": "periods"}` | yes | — | every teacher with `max_hours` |
| `FAIR-<module>` | `balance_load` | `code:` the module's teachers | `{"unit": "periods"}` | no | 2 | every module with two or more teachers |
| `CONT-<module>-<kind>` | `same_resource` | `ref:<module>` and `kind:<kind>` | `{"type": "Teacher", "per": "StudentGroup"}` | no | 3 | every Session row whose teacher pool has two or more teachers |

They are active by default. `Teachers.max_hours` is a number of occupied periods per week (blank for no limit), a hard rule; in the L6 data one period is one hour. Shares are equal (no per-teacher share column). A group keeps the same teacher for all its sessions of one module and kind, not across kinds. Hand-made datasets get none of these.

## Consequences
- The Constraints table shows only rules the user wrote. The score breakdown and the verifier show the derived ones by code, because the prepared dataset carries them.
- `prepare_with_preset` (API, worker, CLI) derives constraints as well as demands. Anything that checks a run uses the prepared dataset.
- A new column `Teachers.max_hours` is a workbook format change: version 2 is **amended**, as in Phase 24 (Amendment 1 of ADR-0007), and the specs say so.
- Compile time grows with the number of derived rules; Phase 25 measures L6 as configuration.
- Per-teacher shares and a "same teacher across kinds" rule are left for later.
