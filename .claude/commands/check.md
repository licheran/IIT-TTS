---
description: Run all quality gates and summarise the results
---
Run, from `backend/`: `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -m "not scale"`.
If `web/` has changes (`git status`), also run from `web/`: `pnpm lint && pnpm typecheck && pnpm test`.
Report pass or fail for each gate. For each failure, give the first error and the likely cause. Do not change tests to make them pass.
