# Phase 6 — Persistence, API, runs and worker

**Goal:** a working back end.

## Read first
- `docs/spec/06-architecture.md` §2, §4, §5, §9

## Tasks
- [x] P6.1 `store/models.py`, `store/db.py` and the first Alembic migration for every table in spec 06 §4, including the partial unique index on published runs.
- [x] P6.2 `store/repositories.py`: dataset save and load to and from the core `Dataset`, table CRUD driven by the preset's sheet definitions, and run lifecycle methods.
- [x] P6.3 API routers `datasets`, `tables`, `io`: every endpoint in spec 06 §5 up to `/preflight`, with the standard error shape.
- [x] P6.4 Runs:
  - `POST /datasets/{id}/runs` snapshots and hashes the dataset, then queues the run.
  - `worker/runner.py` claims runs (`SKIP LOCKED`), runs the pipeline, heartbeats, reports progress, handles cancel, and stores the result and diagnostics.
- [ ] P6.5 Results: `/runs/{id}`, `/assignments`, `/grid`, `/diff`, `/publish` (at most one published run per dataset), and `/export` (HTML through `io/export_html.py` + Jinja2; XLSX; CSV).
- [ ] P6.6 `POST /validate` (FR-14), accepting a workbook with assignments or a FET HTML export.
- [ ] P6.7 Integration tests (SQLite by default; Postgres when `TT_TEST_PG` is set):
  - L6 end to end through the API.
  - Cancel: a long run stops within 2 s and keeps its best solution (`cancelled_partial`).
  - Two workers never claim the same run (Postgres only).
  - A stale-heartbeat run is re-queued.

## Acceptance
- `docker compose up`, then run the smoke script `scripts/smoke.sh`: import `l6.xlsx`, start a run, poll until `succeeded`, fetch the grid for `L6 SE / G1`, and export the HTML.
- All integration tests pass.
