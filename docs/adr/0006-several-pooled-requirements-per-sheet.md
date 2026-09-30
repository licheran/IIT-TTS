# ADR-0006: Several pooled requirements per sheet row

- **Status:** Proposed
- **Date:** 2026-09-30

## Context
The core model has always allowed several pooled requirements per event (`PooledRequirement.ordinal`, spec 02 section 1). The sheet definitions did not: a `SheetDef` had at most one `PooledMapping`, and the workbook writer refused a dataset with a second pooled requirement. The academic preset never needed more, because an activity needs one kind of room.

The exams preset (Phase 11, FR-16) needs two: one hall and several invigilators per exam. P11.4 requires that Phase 11 changes nothing in `core/`, `solver/`, `expand/` or `preflight/`, and says: if it would, write an ADR and fix the abstraction first. `core/sheets.py` is in `core/`, so the sheet definitions have to be generalised before Phase 11, not during it.

## Options
1. **Several `PooledMapping`s per sheet.** Keep `SheetDef.pooled` (ordinal 0) and add `more_pooled` (ordinals 1, 2, …). Columns name their mapping with the fields `pooled_type:<n>` and `pooled_count:<n>`, and `pooled_type`/`pooled_count` mean mapping 0 as before. A mapping may have no type column: then its filter is `all` (any resource of the type), and the requirement exists whenever its count is at least 1.
   *Pros:* the academic workbook is unchanged (same columns, same `format_version`); generic; small change to `io`. *Cons:* a sheet with many different pooled needs grows many columns.
2. **A generic requirements sheet** (target `pooled`, one row per event and requirement). *Pros:* any number of requirements. *Cons:* a new target, a new sheet in every preset or an optional one, and a clumsier workbook for the common case of one or two requirements.
3. **Model invigilators without pooling** (as fixed resources chosen by hand). *Cons:* not what the use case asks (spec 01 section 3), and it hides the problem instead of solving it.

## Decision
Option 1. It is the smallest change that makes the sheet definitions as expressive as the core model for the presets in view, and it leaves the academic format untouched. Option 2 stays open if a preset ever needs an open-ended list of requirements.

## Consequences
- `core/sheets.py`: `PooledMapping.type_column` and `tag` become optional; `SheetDef.more_pooled`; `SheetDef.pooled_mappings` lists them in ordinal order.
- `io/importer.py` and `io/tables.py` read and write each mapping by its ordinal. The academic rules for online activities (no room type and no room count) still apply to mapping 0 when it has a type column.
- No change to the academic workbook format (`format_version` stays 1), to the solver, to the verifier or to pre-flight.
- The change lands before Phase 11, so P11.4's check (no core change during Phase 11) is measured from that commit.
