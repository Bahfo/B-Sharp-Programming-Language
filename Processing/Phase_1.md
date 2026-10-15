# Phase 1 — Expressions, Variables, and Output Parity

Status: IN PROGRESS (started 2026-10-15). Phase 0 accepted; historical results in `Phase_0.md` preserved.

## 1. Exact scope

Target fixtures (only): `Tests/D-Backend/static_vars.bsharp`,
`Tests/D-Backend/static_expr.bsharp`. Both carry `!pragma enforce`, so every
declaration is annotated — the emitter may rely on declared types and reject
anything else with `DBackendError` (honest failure, never silent substitution).

AST kinds to implement (closed set; everything else stays `DBackendError`):
`Number/Boolean/String/Char/None` literals, `UnaryOp` (`-`,`+`,`not`),
`BinaryOp` (`+ - * / %IDIV ~MODULO ^ == != < > <= >=`, `and/or`, `is` alias),
`VariableAssign/MultiAssign/Reassign/Access`, `IncrementNode`,
`PropertyAccess(.type only)`, `CastNode` (numeric sources only),
`CallNode` for `__writeln` (N-arg), `__to_String`, `__format`.

Deliberately OUT (Phases 2–5): control flow, functions, collections/structs,
imports, try/catch, `NaN/Infinity` nodes, `Char/String/Bool` cast sources,
`!pragma precision` codegen (fixtures use enforce-only; runtime renders with
`precision=None` semantics), runtime error-code parity (see §5).

## 2. Dependencies

- Shared frontend `parse_source()` (unchanged) supplies `StatementsNode`.
- `typesys.py` promotion/wrap/`to_f32` rules are the oracle; `instances.py`
  op methods (`division`, `integer_division`, `modulo_division`, `power`,
  `is_equal`, string `addition`/`multiplication`, `_fmt_arg`, `render_value`
  with `precision=None`) define observable behavior.
- New `B_Sharp/Backend/Runtime/bsruntime.d` must land BEFORE emitter ops that
  call it; `driver.build_file` must compile it alongside generated code.
- `diff_phase2.py` minimal hardening (timeouts + exit-code compare) lands
  before the final gate runs.

## 3. Acceptance tests

- `python3 Tests/D-Backend/diff_phase2.py static_vars.bsharp static_expr.bsharp` → ALL PASS.
- New `Tests/D-Backend/phase1_edge.bsharp` (boundaries, neg div/mod, promotion,
  casts, strings, assignment semantics, feature interactions) → differential PASS.
- `python3 -m pytest Tests/ -q --ignore=Tests/test_number_fuzz.py` → green (914 baseline).
- `Tests/golden_runner.py --check` (15) + `conformance_runner.py --check` (26) → green.

## 4. Known risks

- D `%.17g` vs Python `str(double)`: differs on some shortest-round-trip cases
  (e.g. `1/3`); fixtures use `2.5/0.5/3.14/5.0` (verified equal). Residual risk
  documented; exotic doubles deferred.
- D signed overflow is technically UB but wraps on ldc2/dmd; `%`/`~`
  implemented with explicit unsigned-domain helpers to avoid UB entirely.
- Mixed int/float comparisons use D promotion (inexact past 2^53) vs B# exact
  `Fraction` compare — fixtures are same-type; limitation recorded, Phase 5.
- `^` with runtime-negative int exponent: B# returns Double, D needs static
  types → emitter dispatches on syntactic exponent form (negative int literal
  → double path); non-literal exponents take the int path with a runtime abort
  on negative (loud failure, never silent wrong value).
- B# error codes (`RUN100` div-zero etc.) are NOT reproduced as codes; runtime
  helper aborts with message on stderr + exit 1. Code parity is Phase 5.

## 5. Implementation steps (dependency order)

1. [x] Docs: this file + TODO update (no code).
2. [ ] `Runtime/bsruntime.d`: `bsDblStr/bsFltStr`, `bsDiv/bsIdiv/bsMod`,
   `bsPowI/bsPowD`, `bsCast{Long,Integer,Single,Short,Double,Float}`,
   `bsToStr/bsRepr/bsFormat/bsRepeat`, `bsFail`.
3. [ ] `emitter.py`: type map, `(code, btype)` expression protocol, literals,
   unops/binops, vars/const/multi/reassign/access, increment, cast, `.type`,
   `__writeln/__to_String/__format`; symbol table for declared types.
4. [ ] `driver.py`: compile runtime sources alongside generated `.d`.
5. [ ] Harness: timeouts + returncode compare in `diff_phase2.py`.
6. [ ] Iterate fixtures to green; write `phase1_edge.bsharp`; full regressions.

## 6. Execution log

### Step 1 — docs (2026-10-15)

Wrote this file; updated `TODO.md` phase pointer. No code changes.
Tests: none (docs only).

### Step 2 — runtime module (2026-10-15)

Created `B_Sharp/Backend/Runtime/bsruntime.d` (new `module bsruntime`):
`bsFail`, `bsDblStr` (shortest-round-trip + `.0` fix, mirroring Python
`str(double)`), `bsFltStr` (shortest-round-trip, NO `.0` fix — mirrors
`f32_repr`, discrepancy found via differential test, see Step 6),
`bsDiv/bsIdiv/bsMod` (unsigned-domain, wrap-exact), `bsPowI` (modular
binary exponentiation) / `bsPowD`, `bsCast{Long,Integer,Single,Short,
Double,Float}` (trunc/NaN→0/inf-clamp/wrap), `bsRepeat`, `bsToStr`
(writeln semantics: strings raw) / `bsRepr` (format semantics: strings
quoted) / `bsFormat` (`{N}` substitution, unknown index kept).
Verified: `ldc2 -c bsruntime.d` → OK.
Tests: compile-only at this step.

### Step 3 — emitter (2026-10-15)

Rewrote `B_Sharp/Backend/emitter.py` (was 59 lines, 3 node kinds) into a
statically-typed emitter: `B2D` map, `(code, B# type)` expression protocol,
`emit_statement` dispatch, symbol table of declared types. Implemented:
literals with load-time wrap (`wrap_signed` in the emitter, hex fallback
for `long.min`), unops, binops (`+ - *` native + narrow-cast-back,
`/`→`bsDiv`, `%`→`bsIdiv`, `~`→`bsMod`, `^`→`bsPowI`/`bsPowD` with
negative-literal-exponent → Double rule, comparisons + `is`≡`==`,
cross-type `==`→false literal, numeric-Bool `==` via `? 1 : 0` coercion,
`and/or`→`&&`/`||`, string concat/repeat incl. reversed `n * "s"`),
`cast` (numeric sources), `.type` (static), `var/const` (+multi, +`auto`
fallback for dynamic), reassign, `++/--` (pre/post, int-only),
`__writeln` (N-arg), `__to_String`, `__format`. All else → `DBackendError`.
Tests: `static_vars` build+run matched interpreter on first attempt.

### Step 4 — driver (2026-10-15)

`B_Sharp/Backend/driver.py`: added `RUNTIME_DIR`/`RUNTIME_SOURCES`, missing
runtime → `BuildError`, compile command now `[comp, d_path,
bsruntime.d, -of=exe]`. `import bsruntime;` resolves via the explicit file
(no `-I` needed — verified). Tests: both fixtures built (exit 0).

### Step 5 — harness (2026-10-15)

`Tests/D-Backend/diff_phase2.py` minimal hardening: `INTERP_TIMEOUT=60`,
`BUILD_TIMEOUT=300`, `EXE_TIMEOUT=30` constants; `TimeoutExpired` reported
distinctly per stage; stale `.exe` removed before build; exe returncode must
equal interpreter returncode (`EXIT-MISMATCH` otherwise). Deferred to
Phase 6: stderr compare, textual diffs, `.d` retention contract, `.o` policy.

### Step 6 — fixtures green + edge + regressions (2026-10-15)

- `static_vars` OK (5 lines), `static_expr` OK (14 lines) — first attempt.
- Wrote `Tests/D-Backend/phase1_edge.bsharp` (55 writeln lines): narrow-type
  wrap (`200b`→-56, Long/Integer/Short overflow), negative `%`/`~`,
  promotion (`Long+Float`→Double, `Float+Double`→Double, `Single+Single`),
  casts (neg-trunc, `300→Short` wrap), powers (`2^0`, `2.0^3`, `9^0.5`),
  strings (concat incl. `Char+Char`, num/bool concat, `*0`, reversed repeat),
  logic (`and/or/not`, `is` alias, mixed `1==1.0`, `1==true`),
  pre/post `++` value semantics, `const`, multi-assign, `.type` ×3,
  `__format` (computed arg, repeated index, unknown index kept),
  `__to_String` ×3, combined-expression interaction.
- Two fixture bugs fixed (both mine, interpreter-rejected before compiling):
  unannotated `var u` under `!pragma enforce` (SYN075); `Long`-typed sums
  into `Integer`/`Short` decls and `Float+Float` into `Double` decl (ASN005).
- One real backend defect found by differential test and fixed:
  `bsFltStr` appended `.0` but B# `f32_repr` does not (`cast(1,Float)` →
  `"1"` not `"1.0"`). Fixed in runtime; re-ran to green.
- Final: `diff_phase2.py static_vars static_expr phase1_edge` → ALL PASS.
- Out-of-scope `static_control/fn/struct` still fail honestly:
  `BACKEND-ERROR: Unsupported IfNode/FunctionDefNode/StructDefNode`.
- Full suite: `pytest Tests/ --ignore=fuzz` → 914 passed, 10 subtests;
  `test_number_fuzz.py` → 1 passed; golden 15/15; conformance 26/26.

## 7. Test evidence

- `python3 Tests/D-Backend/diff_phase2.py static_vars.bsharp static_expr.bsharp phase1_edge.bsharp` → `ALL PASS` (5 + 14 + 55 lines), exit 0.
- `python3 -m pytest Tests/ -q --ignore=Tests/test_number_fuzz.py -p no:cacheprovider` → `914 passed, 10 subtests passed`, exit 0.
- `python3 -m pytest Tests/test_number_fuzz.py -q -p no:cacheprovider` → `1 passed` (36.6s), exit 0.
- `python3 Tests/golden_runner.py --check` → `All 15 golden program(s) match`, exit 0.
- `python3 Tests/conformance_runner.py --check` → `All 26 conformance program(s) match`, exit 0.
- `python3 Tests/D-Backend/diff_phase2.py` (all 5 defaults) → vars/expr OK;
  control/fn/struct `BUILD-FAIL` with honest `Unsupported …` errors (Phase 2–4 scope).
- No test was weakened, skipped, or rewritten; `phase1_edge.bsharp` fixture
  bugs (SYN075, ASN005) were fixed in the fixture to match established
  interpreter semantics, not the other way around.

## 8. Remaining limitations / discrepancies

- §4 risks stand, plus: `long.min` decimal literal needs the hex-cast fallback
  (`_d_int_literal`); exotic-double rendering (`%.17g` vs shortest-round-trip)
  may differ from Python `repr` outside fixture/edge coverage — no case observed;
  mixed int/float ordering past 2^53 untested by design; `^` with dynamic
  negative int exponent aborts (loud, documented) instead of returning Double;
  runtime error codes/messages not reproduced (stderr + exit 1 only);
  `!pragma precision` unimplemented in codegen; dynamic-mode vars work only
  when the initializer has a Phase-1 static type.
- Files changed in Phase 1: `B_Sharp/Backend/emitter.py` (rewrite),
  `B_Sharp/Backend/driver.py` (runtime sources on compile line),
  `B_Sharp/Backend/Runtime/bsruntime.d` (new), `Tests/D-Backend/diff_phase2.py`
  (timeouts + exit-code compare + stale-exe cleanup),
  `Tests/D-Backend/phase1_edge.bsharp` (new), `Processing/Phase_1.md` + `TODO.md`.
- Pre-existing uncommitted work (`is` keyword, `bsharp.py main()`) still
  uncommitted and untouched by Phase 1 (emitter's `is`≡`==` relies on the
  working-tree parser; committing that work separately is still recommended).
