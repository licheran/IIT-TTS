# Phase 16 — Wiki: troubleshooting

**Goal:** a reader who hits an error or a bad result can look it up, learn what it means and how to fix it.

## Read first
- `docs/spec/03-workbook-format.md` §1 (rule 11, error format) and §3 (validation)
- `backend/src/tts/io/importer.py` and `backend/src/tts/io/tables.py` (every import message)
- `backend/src/tts/preflight/checks.py` (every issue kind)
- `backend/src/tts/store/models.py` and `backend/src/tts/worker/` (run statuses)
- `docs/spec/05-solver.md` (explanations)

## Tasks
- [x] P16.1 `troubleshooting/import-errors.md`:
  - how to read `Sheet!R<row>C<col> [column]: message`;
  - one entry per message the importer emits, each with cause and fix: missing column, required value, duplicate code, unknown code, bad number, time or boolean, bad selector or JSON, unknown constraint type, hierarchy cycle, format version, unknown header, file too large.
- [x] P16.2 `troubleshooting/preflight-issues.md`: one entry per issue kind in `preflight/checks.py` (for example `no_candidate`, `invalid_constraint`, overload, capacity). Each gives its severity, what it means and how to fix it.
- [x] P16.3 `troubleshooting/run-statuses.md`: queued, running, succeeded, infeasible, blocked, invalid, failed, cancelled, cancelled_partial, and a stale run that was re-queued. For each: what happened, and what to do next.
- [x] P16.4 `troubleshooting/infeasible.md`:
  - how to read the conflicting-rules explanation;
  - common fixes: widen availability, add rooms, relax a hard constraint to soft, remove pins;
  - a short FAQ: a slow solve, a poor score, clashes between datasets (`tts clashes`), a row that shows an error.
- [x] P16.5 The troubleshooting check in `test_wiki.py`: every issue kind in `preflight/checks.py` and every run status appears in the pages. A test reproduces each import-error message that has an entry and checks the page quotes it.
- [x] P16.6 Link the error pages from each table page's "typical errors" section (P14.2).

## Acceptance
- Every message the importer and pre-flight can produce, and every run status, has an entry with a cause and a fix.
- The P16.5 checks pass.
