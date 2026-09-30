# Phase 15 — Wiki: constraints and selectors

**Goal:** explain the Constraints sheet, the selector language, and every constraint type in the catalogue, with parameters and examples.

## Read first
- `docs/spec/04-constraints.md` (definitions, the catalogue, the academic defaults)
- `docs/spec/02-domain-model.md` §5 (selectors)
- `backend/src/tts/core/registry.py` (`DECLARED`) and `backend/src/tts/core/constraints/<type>.py` (`Params`)
- `backend/src/tts/presets/*/defaults.py`

## Tasks
- [x] P15.1 `constraints/README.md`:
  - the Constraints sheet in practice: hard vs soft, weight, active;
  - the score as the sum of weight × penalty, and how to read the score breakdown on the Run tab;
  - the rules that always apply without a row (spec 04 §1).
- [x] P15.2 `constraints/selectors.md`:
  - every clause (`all`, `type:`, `code:`, `under:`, `tag:`, `attr:`, `kind:`, `ref:`, `uses:(...)`), combined with `;`;
  - quoting codes that contain spaces, `/`, `;` or `,`;
  - which clauses match resources and which match activities;
  - about ten worked L6 examples, for example every SE group is `under:L6 SE`, and labs holding 60 seats or more is `type:Room;tag:room_type=lab;attr:capacity>=60`.
- [x] P15.3 One page per catalogue type C1–C14. Each has:
  - what it enforces, in plain words;
  - its scope (resources or activities);
  - a params table: name, type, required, meaning;
  - how the penalty is counted;
  - advice on hard vs soft;
  - a JSON example row for the Constraints sheet.
- [x] P15.4 `constraints/defaults.md`: AC-GAPS, AC-TGAPS, AC-TRAVEL (created inactive) and AC-SAT, and the exams preset's EX-SPREAD. For each: what it does, and how to change it or turn it off.
- [x] P15.5 The constraints check in `test_wiki.py`: each type in `DECLARED` has a page, each `Params` field is named on it, and every default constraint code in `presets/*/defaults.py` appears in `defaults.md`.

## Acceptance
- All 14 types, the selector language and the defaults are documented.
- The P15.5 check passes.
- Every JSON example on a type page is accepted by the importer. A test builds a Constraints row from each example and imports it.
