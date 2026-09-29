# Phase 1 — Core model and verifier

**Goal:** the domain-neutral model and an independent checker for any assignment.

## Read first
- `docs/spec/02-domain-model.md` (all)
- `docs/spec/04-constraints.md` §0–§1
- `docs/spec/05-solver.md` §6

## Tasks
- [ ] P1.1 `core/model.py`: frozen Pydantic models for every concept in spec 02 §1, plus `Dataset` (the whole snapshot), `Result` (assignments + chosen resources) and `Violation`. Validate the invariants in spec 02 §2 as model validators where they are local, and in `Dataset.validate()` where they are global.
- [ ] P1.2 `core/hierarchy.py`: `children`, `ancestors`, `exclusive_descendants`, `detect_cycles`, `occupied_resources(event, chosen)` following the occupancy rule (spec 02 §3). Tests cover a grouping parent with exclusive children, nested subgroups, and a cycle.
- [ ] P1.3 `core/timegrid.py`: slot indexing, `allowed_starts(event, time_model)`, `covered_slots(start, duration)`. Tests cover the day end, a break inside the span, a day restriction, and duration 1 and 3.
- [ ] P1.4 `core/selectors.py`: a parser and evaluator for every clause in spec 02 §5, including quoted values and `uses:(…)`. Invalid input raises `SelectorError(position, message)`. Include a hypothesis round-trip test for the parser.
- [ ] P1.5 `core/constraints/` scaffolding: a base protocol and a registry keyed by type name. Implement `verify` for the implicit H0–H5.
- [ ] P1.6 `core/verifier.py`: `verify(dataset, result) -> list[Violation]` running H0–H5 and all active declared constraints that have a registered verifier. Unknown types return a `Violation` of kind `unsupported_constraint` (warning).
- [ ] P1.7 Mini fixtures in `tests/unit/fixtures.py`: builder helpers (`make_dataset(...)`) with no academic words. Build one hand-made case per violation kind (group clash via parent, room double-booking, capacity, filter mismatch, unavailable, pin mismatch, start not allowed).

## Acceptance
- `uv run pytest tests/unit -q` passes. Each violation kind is detected, with exactly the expected refs.
- `uv run mypy src` is clean (strict on core).
- The architecture and core-purity tests pass.

## Out of scope
The solver, I/O and database.
