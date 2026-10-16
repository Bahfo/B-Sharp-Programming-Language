---
name: bsharp-semantic-audit
description: Use to investigate surprising B# behavior, scope/type/call semantics, compatibility risks, conformance gaps, or disagreements between specification and interpreter.
---

# B# Semantic Audit

## Goal

Explain what B# currently does, what the accepted rules say it should do, and whether those sources agree. Do not modify behavior during the audit unless separately authorized.

## Procedure

1. Read `AGENTS.md`, `docs/engineering/SEMANTIC_STABILITY.md`, and `docs/engineering/SEMANTIC_CONTRACT.yaml`.
2. Find the lexer/parser path, AST node, interpreter/runtime implementation, type rules, and relevant tests. Follow actual call paths rather than guessing from a single function.
3. Create a minimal B# example that demonstrates the behavior.
4. Run an existing test or a temporary/non-committed reproduction if the environment supports it. Do not add or modify files during a read-only audit unless requested.
5. Classify the finding as confirmed rule, observed legacy behavior, approved change, or unresolved conflict.
6. Explain the evidence and consequences, including affected neighboring features.
7. Recommend the smallest corrective action, but do not implement it without authorization if it changes observable behavior.

## Report format

- Question investigated
- Minimal reproduction
- Actual result (observed or unverified)
- Relevant implementation path
- Existing tests/specification
- Compatibility classification
- Proposed next step and whether owner approval is required

Never infer that an undocumented behavior is intended, and never assume another language's semantics apply to B#.
