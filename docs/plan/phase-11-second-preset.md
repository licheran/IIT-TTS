# Phase 11 — Second preset: exams

**Goal:** prove that the core is generic (FR-16, NFR-5).

## Read first
- `docs/spec/01-product.md` §3
- `docs/spec/02-domain-model.md` §6

## Tasks
- [x] P11.1 `presets/exams/`:
  - Types: Cohort (exclusive, size), Hall (exclusive, capacity), Invigilator (exclusive).
  - Reference type: Paper.
  - Time: dated days, with sessions AM and PM.
  - Pooled Hall (1) and Invigilator (count by size).
  - Defaults: `min_days_between` for each cohort's exams (soft).
- [x] P11.2 Sheet definitions and labels. A sample workbook goes in `tests/fixtures/exams/`.
- [x] P11.3 An end-to-end test through the CLI and the API.
- [x] P11.4 Confirm with `git diff` that `core/`, `solver/`, `expand/` and `preflight/` did not change. If they did, stop, write an ADR, and fix the abstraction first.

## Acceptance
- The exams sample imports, solves, verifies and exports, and the web UI shows the exams preset's labels, with no changes to core code.
