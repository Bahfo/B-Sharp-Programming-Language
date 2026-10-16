---
name: bsharp-feature-spec
description: Use before implementing a new B# language feature or changing grammar, types, scope, evaluation, runtime values, or externally observable behavior.
---

# B# Feature Specification Workflow

1. Read `AGENTS.md` and `docs/engineering/SEMANTIC_STABILITY.md`.
2. Inspect the existing implementation and tests to establish the baseline. Do not assume the feature is absent or present from prior discussion alone.
3. Write a specification using `docs/engineering/FEATURE_SPEC_TEMPLATE.md`.
4. Define valid and invalid syntax, runtime meaning, scope, types, initialization/evaluation order, errors, edge cases, and interactions with existing features.
5. Mark assumptions and unresolved questions explicitly. Do not silently select semantics for unresolved cases.
6. Identify compatibility risks and acceptance tests, including negative and regression cases.
7. Present the specification for owner approval. Do not implement a semantic feature before approval.
8. After approval, implement only the accepted scope and verify against the acceptance criteria.
9. Update the language reference, tests, and semantic contract where appropriate, but only within the approved task.
