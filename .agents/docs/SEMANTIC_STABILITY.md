# B# Semantic Stability Policy

## Default

Existing B# behavior is compatibility-sensitive. A behavior being surprising, inconsistent with another language, or inconvenient is not sufficient reason to change it.

A semantic change requires explicit owner authorization for the specific rule being changed. Tests passing after a change do not by themselves prove the change was authorized or correct.

## Known owner-confirmed behavior

These rules were explicitly stated by the language owner and must be protected by characterization tests:

1. Declarations inside `if` blocks leak into global state by design.
2. Declarations inside loop bodies do not leak into global state.
3. Declarations inside function bodies do not leak into global state.
4. A function name used as an expression evaluates to a function value.
5. `Function` is a usable annotation for variables holding function values.
6. Function values can be passed as arguments and invoked indirectly through function-valued parameters or variables.

Do not normalize these rules to make scope behavior uniform, and do not narrow first-class function behavior as a side effect of type-system or interpreter changes. Verify exact implementation details and add targeted tests before refactoring affected code.

## Semantic change checklist

For every proposed change to language behavior, identify:

- Current behavior, backed by code and a test or reproducible program.
- Desired behavior, backed by explicit owner authorization or an accepted language specification.
- Syntax changes, if any.
- AST and parser consequences.
- Scope, environment, and name-resolution consequences.
- Runtime value and type-system consequences.
- Error and failure behavior.
- Backward-compatibility impact.
- Regression tests and acceptance criteria.
- Documentation that needs updating.

## Distinguish quirks from desired rules

When an unexpected behavior is discovered, classify it as:

- **Confirmed compatibility rule:** owner has explicitly decided it is intended.
- **Observed legacy behavior:** currently reproducible but not yet endorsed as permanent design.
- **Approved change:** a new rule authorized by the owner and documented.
- **Unresolved conflict:** implementation, tests, and specification disagree.

Do not silently promote observed legacy behavior into a language guarantee. Do not silently discard it either. Record the evidence and request a decision when the distinction affects the task.

## Specifications and tests

- Grammar documents syntax; it does not define all runtime semantics.
- Semantic documentation defines intended behavior; tests verify implementation.
- Characterization tests record existing behavior before refactoring.
- Conformance tests verify accepted language rules.
- Golden baselines must not be updated solely because output changed.
- An authorized change should update the specification and tests in the same work item when practical.

## Feature proposals are not implementation facts

A proposed container design, OOP model, foreign-function interface, graphics binding, or grammar-driven parser is not an existing capability merely because it was discussed or documented as a proposal. Inspect the repository and accepted feature specification before assuming it is implemented. Clearly label proposed, partially implemented, and supported behavior separately.
