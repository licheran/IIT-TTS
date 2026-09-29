# Phase 0 — Project setup

**Goal:** a working, empty repository with tooling, CI and a compose skeleton.

## Read first
- `docs/spec/06-architecture.md` §3, §7, §8, §9
- `CLAUDE.md`, `backend/CLAUDE.md`, `web/CLAUDE.md`

## Tasks
- [x] P0.1 `backend/`: `uv init --package tts` with `src/tts/` and the empty package directories from spec 06 §3 (each with `__init__.py`). Add the runtime dependencies (ortools, pydantic, fastapi, uvicorn[standard], sqlalchemy, alembic, psycopg[binary], openpyxl, pandas, jinja2, beautifulsoup4, typer) and the dev dependencies (pytest, hypothesis, ruff, mypy, httpx, import-linter). Configure ruff and mypy in `pyproject.toml`, with strict mypy for `tts.core`. Register pytest markers: `scale`, `integration`.
- [x] P0.2 `backend/src/tts/cli.py`: a Typer app named `tts` with stub commands `solve`, `validate`, `import-fet` and `export` that exit with "not implemented". Register it as a console script.
- [x] P0.3 `backend/src/tts/api/main.py`: a FastAPI app with `GET /health` returning `{"status":"ok"}`, plus a test.
- [x] P0.4 `backend/tests/unit/test_architecture.py`: the dependency rules from spec 06 §3 and the core-purity word check (it passes on the empty packages).
- [ ] P0.5 `web/`: Vite React-TS with pnpm, TypeScript strict, Tailwind, shadcn/ui init, TanStack Table and Query, vitest, Playwright, eslint and prettier. Scripts: `dev`, `build`, `test`, `lint`, `typecheck`, `e2e`, `gen:api` (openapi-typescript from `http://localhost:8000/openapi.json` to `src/api/schema.ts`). The placeholder home page calls `/health`.
- [x] P0.6 `docker-compose.yml`: `db` (postgres:16, with a healthcheck), `api` (uvicorn, depends on db), `worker` (running `python -m tts.worker.main`, a stub loop that sleeps), `web` (vite dev). Add `.env.example` with the variables from spec 06 §9.
- [x] P0.7 `.github/workflows/ci.yml`: jobs `backend` (uv sync, ruff, mypy, pytest -m "not scale") and `web` (pnpm install, lint, typecheck, test). Add a nightly schedule for `pytest -m scale`.
- [ ] P0.8 Record the pinned versions in `docs/STATUS.md`. Add an `ADR` link check to CI (a markdown link checker on `docs/`).

## Acceptance
- `cd backend && uv run ruff check . && uv run mypy src && uv run pytest` passes.
- `cd web && pnpm lint && pnpm typecheck && pnpm test` passes.
- `docker compose up --build` starts. `curl localhost:8000/health` returns `{"status":"ok"}` and the web page shows "API: ok".
- CI is green on the pull request.

## Out of scope
Any domain code.
