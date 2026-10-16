# B# Testing and Verification Policy

## Test principles

- A test pass is evidence for the tests that ran, not proof of every language behavior.
- Add regression tests for discovered defects and characterization tests before refactoring subtle behavior.
- Keep tests independent, deterministic, and clear about expected results.
- Preserve existing golden, corpus, stress, and conformance tests.
- Do not turn failing tests into skipped tests, reduce assertions, broaden exceptions, or change expected output without authorization for the underlying semantic change.
- Do not claim a suite is complete if a subset was excluded.

## Find the authoritative commands

Before running tests, inspect the current repository instructions, `pyproject.toml`, test configuration, scripts, and CI workflows. Use the commands currently defined there. A previously used command is not guaranteed to remain current.

A previously recorded B# command is `pytest Tests/ --ignore=fuzz`; verify that this command and directory layout still apply before using it as the canonical suite.

## Verification sequence

1. **Baseline:** record working-tree state and reproduce the relevant behavior before editing when feasible.
2. **Focused tests:** run the smallest test that proves the requested behavior.
3. **Adjacent regression tests:** cover nearby syntax, runtime operations, error paths, and known quirks.
4. **Full applicable suite:** run the repository's defined regression suite when feasible.
5. **Static checks:** run only checks already configured or authorized for the repository.
6. **Diff validation:** run `git diff --check` when Git is available and inspect the whole diff.

## Report exact evidence

For every command, report whether it passed, failed, was skipped, or was not run. Include relevant output or counts when available. Give a concrete reason for skipped or unavailable tests. If a test cannot run because of an environment or dependency problem, do not present it as passing.

## Test-baseline changes

Changing golden outputs, snapshots, corpus expectations, conformance baselines, or test assertions is a compatibility-sensitive operation. Require explicit authorization and record:

- Why the old expectation was incorrect or no longer desired.
- The authorized new language rule.
- Why the new expectation is correct.
- The relevant test results before and after the change.

Do not generate new snapshots automatically and accept them without review.
