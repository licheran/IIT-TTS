# Phase 17 — Wiki: exams preset

**Goal:** document the exams preset's tables, for readers who use it instead of the academic preset.

## Read first
- `backend/src/tts/presets/exams/sheets.py`, `types.py`, `labels.py` and `defaults.py`
- `backend/tests/fixtures/exams/make_exams.py` (the sample)
- The academic table pages from Phase 14, which shared sheets link to

## Tasks
- [ ] P17.1 `exams/README.md`: what differs from the academic preset (dated days, AM and PM sessions, cohorts, halls, invigilators, papers), and how to start one.
- [ ] P17.2 One page per exams sheet that differs from its academic counterpart (for example Days, Sessions, Cohorts, Halls, Invigilators, Exams with its hall and invigilator columns), in the same format as Phase 14. Sheets that are the same link to the academic pages.
- [ ] P17.3 The exams check in `test_wiki.py`: each exams `SheetDef` has a page or links to its academic page, and every column is listed.

## Acceptance
- Every sheet of the exams preset is covered, and the P17.3 check passes.
