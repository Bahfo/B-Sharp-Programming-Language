---
name: bsharp-safe-change
description: Use when modifying, refactoring, fixing, or reviewing B# source code while preserving existing language semantics and repository conventions.
---

# B# Safe Change Workflow

1. Read root `AGENTS.md` and the relevant change-control, semantic-stability, and testing policies.
2. Inspect the Git working tree; preserve user changes.
3. Locate the exact code path, callers, tests, and documentation relevant to the request.
4. Classify the change as non-semantic, behavior-preserving implementation work, or semantic/compatibility work.
5. For semantic work, do not proceed until the exact behavior change is explicitly authorized and acceptance criteria are clear.
6. Make the smallest patch possible. Do not fold in unrelated cleanup, renames, style rewrites, or dependencies.
7. Add tests that prove the requested result and protect neighboring behavior.
8. Run focused tests, adjacent regressions, and the full applicable suite when feasible.
9. Inspect the complete diff and verify that tests, baselines, comments, and configuration were not altered without cause and authorization.
10. Report changed files, actual test results, tests not run, semantic impact, and remaining risks.

## Stop conditions

Stop before making a behavior-changing decision if the accepted spec, tests, source, or owner instructions conflict. Report the conflict and evidence. Never weaken a failing test merely to make the suite green.
