# Phase 9 — Templates (rules to activities)

**Goal:** declare teaching structure once, and generate the activities from it.

## Read first
- `docs/spec/05-solver.md` §2
- `docs/spec/03-workbook-format.md` (Templates sheet)

## Tasks
- [x] P9.1 `expand/templates.py`: modes `joint`, `per_group` and `batched`; stable codes; lecture-before-tutorial `order` constraints; idempotent re-expansion.
- [x] P9.2 `expand(ds, commit=False)` returns a diff (added, changed, removed). The API is `POST /datasets/{id}/expand`.
- [x] P9.3 UI: a Templates tab, plus a preview dialog showing the diff before commit.
- [ ] P9.4 `tests/fixtures/l6/templates.xlsx`: express the L6 structure as templates. Test that expansion matches the fixture's per-module group coverage and its LEC/TUT counts (`expected.json` → `modules`).

## Acceptance
- The P9.4 test passes. Re-expanding twice changes nothing, and hand-made activities are untouched.
