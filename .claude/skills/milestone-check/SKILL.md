---
name: milestone-check
description: Verify a milestone's definition of done (spec section 15) plus the section 16 checklist, run all tests, report pass/fail per item. Use before calling any milestone done.
---

# milestone-check

Input: milestone id (M0–M8).

1. Read the milestone row in `docs/spec/MVP-technical-spec.md` §15 and every section it touches; list each "definition of done" clause as a checklist item.
2. Run `make lint typecheck test` (and golden/property tests, AI evals, Playwright where the milestone has them). Capture real output.
3. Check the §16 definition of done: import-linter, adapters only, tests added, expand→contract migrations, feature flag, READMEs + `docs/decisions.md`.
4. Confirm nothing post-MVP was built and scope stayed inside the milestone.
5. Confirm architecture-reviewer and security-reviewer were run and findings resolved.
6. Report a table: item → PASS / FAIL / NOT RUN with evidence (command output or file:line). A skipped check is NOT RUN, never PASS.
7. Milestone is done only if every item is PASS.
