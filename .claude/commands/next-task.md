---
description: Pick up the next open task from the current phase and complete it
---
1. Read `docs/STATUS.md` and find the current phase and the first unticked task in its phase file under `docs/plan/`.$ARGUMENTS
2. Read the phase file's **Read first** specs, but only the sections that task needs.
3. Briefly state the task, the files you will touch, and the tests you will add. If anything is ambiguous, stop and ask.
4. Write the tests first where practical, then implement.
5. Run `/check`. Fix any failures without weakening the tests.
6. Tick the task box, add a line to the log in `docs/STATUS.md`, and commit as `<type>(<scope>): <summary> [P<phase>.<task>]`.
7. Report what changed, the test results, and any follow-ups. Do not start the next task unless asked.
