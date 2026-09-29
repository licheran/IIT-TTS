# ADR-0003: Database table as the run queue (v1)

- **Status:** Accepted
- **Date:** 2026-09-29

## Context
Solves are long-running (seconds to minutes), need progress and cancel, and there is one institute per deployment.

## Options
1. **Celery or RQ with Redis.** Proven, but adds a broker and more operational parts.
2. **FastAPI background tasks.** Simple, but tied to the API process, lost on restart, and blocks scaling.
3. **A `run` table with `SELECT … FOR UPDATE SKIP LOCKED`** claimed by separate worker processes.

## Decision
Option 3, with heartbeat-based recovery of stale runs (spec 06 §2).

## Consequences
- No extra infrastructure. Progress and cancel are just columns.
- Revisit if there are many concurrent tenants.
