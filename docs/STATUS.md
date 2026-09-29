# Status

**Current phase:** 0 — [Project setup](plan/phase-00-setup.md)
**Next task:** P0.2
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
