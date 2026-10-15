# B# D Transpiler — Project TODO (authoritative checklist)

## Overall objective

Develop the existing B#-to-D transpiler (`B_Sharp/Backend/`) into a complete,
semantics-preserving native compilation backend. Final goal: reproduce the
established interpreter behavior through transpilation — language constructs,
type rules, runtime behavior, builtins, pragmas, imports, errors, and
feature interactions.

## Architectural constraints (non-negotiable)

- [x] Interpreter semantics + shared frontend are the source of truth.
- [x] Reuse `B_Sharp/frontend.py` `parse_source()` / `FrontendResult`; no second lexer/parser/pragma processor.
- [x] Never modify interpreter behavior to fit backend limitations.
- [x] No alternative language engine; B#→D type mapping does NOT imply semantic equivalence — use a D runtime where needed.
- [x] Never silently ignore unsupported nodes or emit plausible-but-wrong code (`DBackendError` is the honest signal).
- [x] Keep generated D readable/debuggable.
- [x] Small, independently verifiable steps; compilation success ≠ correctness.
- [x] `Processing/TODO.md` stays synchronized with phase records after every step.

## Pre-existing uncommitted work (preserved, NOT authored by Phase 0)

Recorded 2026-10-15 via `git diff`; left untouched per "never discard uncommitted work":

- [x] `B_Sharp/tokens.py`: `KEYWORDS += ["is"]` (was absent at HEAD).
- [x] `B_Sharp/ASTNodes/parser.py`: `and_expression` now wraps new `is_expression`
      (`comparison` → `is` → `and` → `or`); `is_expression` placement reordered.
- [x] `B_Sharp/ASTNodes/interpreter.py`: `visit_BinaryOpNode` treats
      `KEYWORD "is"` as `is_equal` incl. precision-commit path (+ unrelated
      whitespace reflow of several `res.failure(...)` calls).
- [x] `bsharp.py`: `main()` extraction + `KeyboardInterrupt` → exit 130
      (build/run/outer). `test.bsharp` (untracked) is absent from workdir.

## Phases and acceptance criteria

### Phase 0 — Audit + baseline + harness + roadmap (current)

- [x] Deep audit of lexer/parser/nodes/frontend/interpreter/typesys/builtins/
      instances/pragmas/imports/errors/backend/build-path/tests (4 parallel
      audit tracks, findings verified against source).
- [x] `Processing/TODO.md` + `Processing/Phase_0.md` created.
- [x] Reproducible baseline recorded (commands + exit codes + counts).
- [x] AST → interpreter → backend coverage map.
- [x] `diff_phase2.py` validated / limitations documented.
- [x] Smallest reliable end-to-end path demonstrated.
- [x] Runtime/codegen invariants + dependency-aware roadmap.
- [x] No transpiler feature implementation in Phase 0 (only docs + probes in /tmp).
- [ ] Acceptance gate sign-off and Phase 1 scoping (this item closes Phase 0).

### Phase 1 — Static numeric/string core + vars + `__writeln` parity (COMPLETE, gate pending)

Scope: `Number/Boolean/String/Char/None` literals, `BinaryOp` arithmetic
(`+ - * / %IDIV ~MODULO ^`) + comparisons (`== != < > <= >=`, `is` alias) +
`and/or/not` with short-circuit, `var/const` typed decl + reassign + `++/--`,
`VariableAccess`, `__writeln` N-arg parity via D runtime rendering.
Acceptance: `static_vars.bsharp` + `static_expr.bsharp` pass `diff_phase2.py`
(byte-identical stdout, exit 0); `test_llvm_types` semantics pinned for the
covered subset (wrapping, `/`→Double, `%`/`~`, `cast`, string `+/*`).
Result 2026-10-15: ALL PASS (`static_vars` 5 lines, `static_expr` 14 lines,
new `phase1_edge` 55 lines); full suite 914 + fuzz 1 + golden 15/15 +
conformance 26/26 green. Evidence in `Processing/Phase_1.md` §6–§7.

### Phase 2 (proposed) — Control flow

`If/elif/else` (+ `then` + expression form), `While/Do/For` (+`then` blocks),
`Break/Continue/Pass`, scoping (`BodyScopeContext` leak rules).
Acceptance: `static_control.bsharp` passes `diff_phase2.py`.

### Phase 3 (proposed) — Functions

`FunctionDef/Call/Return`, arg binding (positional/named/defaults), recursion
(depth 500), return-type checks, closures.
Acceptance: `static_fn.bsharp` passes `diff_phase2.py`.

### Phase 4 (proposed) — Collections/structs/methods/indexing/slicing

`List/Array/Tuple`, `IndexAccess/Assign`, `Slice`, `MethodCall`
(push/append/swap/delete/drop), `StructDef`, `PropertyAccess/Assign`, `.type/.length`.
Acceptance: `static_struct.bsharp` + golden `05/06` pass differentially.

### Phase 5 (proposed) — Builtins/pragmas/imports/errors

All 20 builtins, `!pragma enforce/precision` per-file isolation,
`using` imports, `TryCatch`, `NaN/Inf/Empty`, error-code parity
(`RUN*/ASN*/MOD*/CMP*` observable behavior).
Acceptance: full golden (15) + conformance (26) triple
(stdout/stderr/exit) parity via compiled exes.

### Phase 6 (proposed) — Driver hardening + CI

Timeouts, stderr/exit comparison in harness, `.d` retention contract,
`Runtime/` packaging on compile command line, `.o` cleanup, SDK `build` verb.
Acceptance: harness compares stdout+stderr+exit with diffs; CI runs
interp suite + golden + conformance + diff on every change.

## Missing-feature inventory (backend supports ~3/39 node kinds)

Emitter handles ONLY: `StatementsNode`, `CallNode(__writeln, 1×StringNode)`,
`StringNode`. Everything else → `DBackendError` → `BuildError`:

- [ ] Vars: `VariableAssign/MultiAssign/Reassign/Access`, `Increment`
  (DONE for the Phase-1 static subset in `emitter.py`; control/fn/data nodes pending)
- [ ] Expr: `Number/Boolean/Char/None/NaN/Infinity/Unary/Binary/Cast`
  (DONE except `NaN/Infinity` nodes and non-numeric cast sources)
- [ ] Control: `If/While/Do/For/Break/Continue/Pass`
- [ ] Fn: `FunctionDef/Call(general)/Return`
- [ ] Data: `List/Tuple/IndexAccess/IndexAssign/Slice/MethodCall/PropertyAccess/PropertyAssign/StructDef/Import/TryCatch`
- [ ] Builtins beyond 1-string `__writeln` (19 more incl. `__format`, `__to_*`, `__is_*`, `__read*`, `__time__`)
- [ ] `Backend/Runtime/` + `main.d` (both empty) — no D runtime for wrapping/promotion/precision/containers/errors
- [x] Pragmas in codegen (`enforce` static types honored via declared-type
  emission; `precision` quantize+render still pending → Phase 5)
- [ ] `ContainerNode` has no interpreter visitor either (`RUN001`) — spec gap shared by both routes

## Known semantic discrepancies / ambiguities (do NOT resolve by simplification)

- [ ] `%` lexes to `IDIV`, `~` to `MODULO` (swapped vs convention); `**`→SYN005, `^`=power.
- [ ] `...` may emit `ELLIPSIS` + extra `DOTDOT/DOT` (missing `elif`).
- [ ] `cast` is contextual (`cast(` only); bare `cast` is a variable.
- [ ] `is` is left-assoc `BinaryOp`, no type-test distinction; `a is B is C` chains while `a==b==c`→CMP001.
- [ ] `2^3^4` is NOT right-assoc (stray `^` after `2^3`).
- [ ] Postfix `++` bare-`IDENT` only; `a.b++`/`a[i]++` rejected.
- [ ] `else` accepts bare statement without `then` (unlike `if/while/for`).
- [ ] `ifdef` is a stub (`print("Hi")`, returns None); `[#...]` missing `]` unchecked.
- [ ] `CALLER_MACROS` lists `pragma,panic,allow,remember` but only `pragma` is implemented.
- [ ] `bsharp.py` documents `bsharp run <file>` but only `bsharp <file>` works.
- [ ] Docs vs implementation: `CHANGELOG 0.2.0` says `bsharp build` "intentionally left unimplemented" while driver+emitter exist (minimal stub).

## Current phase / task

- Current phase: **Phase 1** (expressions, variables, output parity — IN PROGRESS).
- Current task: **runtime → emitter → driver → harness → fixtures green → edge + regressions → gate**.
- Phase 0 gate: accepted; `Processing/Phase_0.md` frozen as historical record.

## Status board

- Completed: deep audit (4 tracks); baseline suite (914 passed); golden (15/15);
  conformance (26/26); diff harness baseline (5 BUILD-FAIL as designed);
  minimal E2E path (`__writeln("hello")` → `.d` → `ldc2` → `hello`); docs created.
- Phase 1 complete: runtime + emitter + driver + harness hardening;
  `static_vars` (5) + `static_expr` (14) + `phase1_edge` (55) ALL PASS;
  full suite 914 + fuzz 1 + golden 15/15 + conformance 26/26 green.
- In progress: Phase 1 acceptance gate sign-off (STOP here; do not start Phase 2).
- Blocked: none (compilers `ldc2+dmd+dub` present; no installs needed).
- Risks (open): no D runtime yet (wrapping/precision/containers); harness
  stdout-only + missing timeouts; `.d "(removed...)"` string contract;
  stale `Tests/D-Backend/*.o` + `golden_runner` no-timeout vs conformance 60s;
  `ContainerNode`/`ifdef` spec gaps; uncommitted `is` + `main()` work must be
  committed separately before Phase 1 diffs.

## Required regression tests (run + record every step)

- [x] `python3 -m pytest Tests/ -q --ignore=Tests/test_number_fuzz.py` → 914 passed
- [x] `python3 Tests/golden_runner.py --check` → 15/15
- [x] `python3 Tests/conformance_runner.py --check` → 26/26
- [x] `python3 Tests/D-Backend/diff_phase2.py` → Phase 0: 5 BUILD-FAIL (expected);
  Phase 1: `static_vars` + `static_expr` + `phase1_edge.bsharp` ALL PASS
- [x] Minimal E2E: `emit_d` → `ldc2` → exe prints `hello`, exit 0
- [x] `Tests/test_number_fuzz.py` → 1 passed (36.6s, run in Phase 1)
- [x] Post-step rule: narrow tests → diff tests → full regression → update both docs

## Dependencies between phases

`Phase 1 (expr/vars/runtime-render)` → `Phase 2 (control/scoping)` →
`Phase 3 (functions/frames)` → `Phase 4 (containers/structs)` →
`Phase 5 (builtins/pragmas/imports/errors)` → `Phase 6 (harness/CI)`.
`Backend/Runtime/` must land with Phase 1 (render/wrap) and grow each phase;
harness upgrade (Phase 6) depends on Phases 1–5 producing comparable exes.
