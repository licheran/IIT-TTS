# Status

**Current phase:** 0 — [Project setup](plan/phase-00-setup.md)
**Next task:** P0.5
**Format version:** workbook `format_version` 1

## Pinned versions
_To be recorded in P0.8._

## Open questions (need answers from the user)
- [ ] Real group sizes and room capacities, to replace the L6 fixture assumptions.
- [ ] Teacher codes: can one person have several codes, or can one code refer to different people across universities?
- [ ] Do universities or levels use different teaching days or block lengths?
- [ ] Travel times between buildings (GP, Java, Rama, Dialog, Spencer), and whether a building change needs a free period.
- [ ] One institute-wide dataset, or staged solving per level?
- [ ] Is the repository public or private? The L6 fixture contains real teacher codes (see `backend/tests/fixtures/l6/README.md`).

## Log
| Date | Task | Notes |
|---|---|---|
| 2026-09-29 | — | Repository foundation: specs, plan, ADRs, Claude Code setup, L6 fixture source. |
| 2026-09-29 | — | Renamed product to IIT-TTS (IIT TimeTabling Solution); Python package and CLI renamed `timetabler` → `tts`. |
| 2026-09-29 | P0.1 | `backend/` uv package `tts` with empty package tree, exact-pinned deps (`uv.lock` committed), ruff, mypy (strict override for `tts.core.*`), pytest markers `scale`/`integration`. Smoke test imports every package. Toolchain: uv 0.12.20, Python 3.12.10, Node 24.18.0, pnpm 12.6.0, Docker 29.8.1. Console script is still the `uv init` placeholder (`tts:main`); P0.2 replaces it with `tts.cli:app`. |
| 2026-09-29 | P0.2 | `tts` Typer app with stub `solve`, `validate`, `import-fet`, `export` (exit 1, "not implemented"), registered as `tts.cli:app`. |
| 2026-09-29 | P0.3 | FastAPI app in `tts/api/main.py` with `GET /health` and an integration test. Follow-up: Starlette's `TestClient` now warns that `httpx` is deprecated in favour of `httpx2`; spec 06 §7 names `httpx`, so left unchanged pending a decision. |
| 2026-09-29 | P0.4 | `tests/unit/test_architecture.py`: AST-walk dependency rules (internal packages and third-party allowlists per package, spec 06 §3) and a tokenize-based core-purity scan of `core`, `solver`, `expand`, `preflight`. Purity matches whole words (camelCase and snake_case split, plurals folded), skips comments, docstrings and dunders, so `grouping_node` passes while `group` fails. Exceptions go in `PURITY_ALLOWLIST` with a reason (empty). Meta tests prove both scanners catch seeded violations. import-linter is installed but not used. |
| 2026-09-29 | P0.6 | `docker-compose.yml` (`db` postgres:16 + healthcheck, `api`, `worker`, `web`), `backend/Dockerfile` (uv, `--frozen --no-dev`), stub worker `tts/worker/main.py` with a test, `.env.example` (spec 06 §9 vars, plus POSTGRES_* and VITE_API_URL). **Only `docker compose config` was validated.** `docker compose up --build` has not been run: the network was unreachable when this was written and `web/` is not scaffolded yet (P0.5). Re-verify at phase acceptance. |
| 2026-09-29 | P0.7 | `.github/workflows/ci.yml`: `backend` (uv sync --frozen, ruff check + format, mypy, `pytest -m "not scale"`), `web` (pnpm install --frozen-lockfile, lint, typecheck, test) and a nightly `scale` job (tolerates pytest exit 5 while no scale tests exist). YAML parses; **not yet run on GitHub**. The `web` job needs `packageManager` in `web/package.json` and a committed `pnpm-lock.yaml` (P0.5). |
