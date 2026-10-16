# Change Control for B#

## Purpose

Keep agent-assisted changes small, reviewable, and compatible with existing B# behavior.

## Change classes

### Class A — Non-semantic maintenance

Examples: typo correction in documentation, internal readability changes proven not to affect behavior, or test diagnostics that do not change assertions.

Required: inspect scope, make a small patch, run applicable checks, and review the diff.

### Class B — Implementation change with intended behavior preserved

Examples: internal refactoring of parser or interpreter code, performance improvements, error-path cleanup that preserves the externally observable contract.

Required: establish a baseline, add or use characterization tests, isolate refactoring from feature changes, run focused and regression tests, and document evidence that behavior was preserved. If equivalence is uncertain, treat the task as Class C.

### Class C — Semantic or compatibility change

Examples: grammar or keyword changes, scope/name resolution, type rules, evaluation order, function/call semantics, reference behavior, container/class behavior, error behavior, import initialization, or changes to expected outputs.

Required before implementation:

1. Explicit authorization from the language owner for the specific behavior change.
2. A written old-versus-new behavior statement.
3. Defined acceptance tests and compatibility impact.
4. Identification of affected subsystems and known callers.

Required after implementation: focused tests, regression tests, full applicable suite, diff review, and an accurate report. Authorization for one behavior does not authorize adjacent semantic changes.

## Standard procedure

1. Inspect `git status --short` and relevant diffs. Do not overwrite user changes.
2. Inspect only the source, docs, and tests needed to understand the task; widen the search when dependencies are discovered.
3. Record current behavior before editing, using focused tests or existing examples where possible.
4. Establish the allowed file and behavior scope.
5. Make the minimum cohesive change. Avoid combining refactoring, formatting, new dependencies, and semantics in one patch.
6. Run focused tests and then the relevant regression suite.
7. Inspect `git diff --check` and the complete diff.
8. Report evidence, gaps, and remaining issues.

## Stop conditions

Stop before a behavior-changing edit if:

- An approved specification conflicts with current code or tests.
- A required semantic choice is unspecified.
- A change would require weakening a test or changing a baseline without authorization.
- Existing user changes make a safe patch unclear.
- The proposed fix expands into an unrelated subsystem.

When stopped, report the exact evidence and the smallest decision needed. Do not invent an answer merely to keep implementation moving.

## Files and operations needing separate approval

Unless explicitly requested, do not modify dependency manifests, lockfiles, CI workflows, packaging, release configuration, golden baselines, language grammar, public APIs, or compatibility contracts. Do not commit, push, publish, release, or deploy.
