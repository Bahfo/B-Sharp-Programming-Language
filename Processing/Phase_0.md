# Phase 0 — Deep Audit, Baseline, Harness Assessment, Roadmap

Date: 2026-10-15. Status: executed; acceptance gate + Phase 1 proposal at §10.
No transpiler features implemented in Phase 0 (docs + `/tmp/opencode` probes only).
Pre-existing uncommitted changes preserved untouched (see §8).

## 1. Audit scope and inspected modules

Four parallel read-only audit tracks, findings verified against current source
(not prior reports):

- Track A (frontend): `B_Sharp/lexer.py` (537 lines), `B_Sharp/tokens.py`,
  `B_Sharp/ASTNodes/parser.py` (2343 lines), `B_Sharp/ASTNodes/nodes.py`
  (509 lines), `B_Sharp/frontend.py`. Produced: 39-node inventory, token/
  keyword tables, precedence chain, statement constructs, SYN/CMP codes,
  10 ambiguities.
- Track B (execution): `B_Sharp/ASTNodes/interpreter.py` (~2112 lines, 37
  visitors + helper), `B_Sharp/ASTNodes/instances.py` (~3067 lines). Produced:
  visitor table, value-class semantics, scope/call/control-flow rules, full
  RUN/ASN/MOD/CMP/MTH code map, eval-order/side-effect rules, numeric-op trace.
- Track C (types/builtins/macros/errors): `B_Sharp/typesys.py` (279),
  `B_Sharp/builtins.py` (263, 20 builtins), `B_Sharp/CodeExecution/
  caller_macros.py` (341) + `__predefined.py` (42), `B_Sharp/Errors/
  error_catalog.py` (987) + `errors.py` (224). Produced: type table +
  promote/convert/wrap/narrowing, builtin behaviors, pragma/import mechanics,
  error taxonomy.
- Track D (backend/tests): `B_Sharp/Backend/{driver,emitter}.py`,
  `Backend/Runtime/` (empty), `Backend/main.d` (empty), `bsharp.py` build path,
  `Tools/emit_d.py` + `dump_ast.py`, `Tests/D-Backend/*` (5 fixtures + harness),
  `Tests/test_*.py` (22+) + `data_types/`, `golden/` (16 corpus) +
  `conformance/` (26 manifest), `SDK/dub.json` + `shell.d`. Produced:
  emitter coverage, driver gaps, harness gap list (6 items), fixture roles.

## 2. Verified architecture and semantic contracts

- Pipeline: `Lexer.tokenize()` → `preprocess_pragmas()` (per-file `FileConfig`,
  leading `!pragma` only, REPL merges `<stdin>`) → `Parser.parser()` →
  `FrontendResult(ast_root: StatementsNode, file_config, error)`.
  Entry: `B_Sharp/frontend.py:24-43`. Both interpreter and backend MUST use it.
- Grammar (lowest→highest): `expression → or (and…) → and (is…) → is
  (comparison…)` [working tree; HEAD lacks `is`] `→ comparison (single
  ==/!=/</>/<=/>=, 2nd → CMP001) → term (+-) → factor (*/÷/%IDIV/~MODULO) →
  unary (+/-/not) → power (^, single, RHS via unary) → call → atom`.
  `;`≡newline; blocks need `{}` or `then` (`else` allows bare stmt).
- Execution: tree-walk `Interpreter.visit()` → `visit_{Type}لیک`, `RunTimeResult`
  error/return/break/continue bubbling; conditions/statements `commit()` under
  file precision; `and/or` short-circuit; calls evaluate callee→args L-to-R.
- Types: fixed-width `Short:i8 < Single:i16 < Integer:i32 < Long:i64`,
  `Float:f32 < Double:f64` (`typesys.py:76-99`); defaults `Long/Double`;
  suffixes `l/i/s/b/f/d(+D)`; two's-complement wrap; `to_f32` binary32;
  `promote()` (same→same, int→wider, float-mix→Double, `Long+Float`→Double);
  kind-strict narrowing (`context_literal`); `convert_numeric` (NaN→0,
  inf→clamp, float→int trunc+wrap); decimal `precision 0-12` rest-points
  (store/return/compare/test/yield) + `render_value` agreement.
- Imports: isolated module `Context` + builtins; importer gets copies
  (`commit` under importer cfg); missing module → `RUN026` at parse.
- Errors: `Error(code, context)` via catalog templates; interpreter rewrites
  `BinaryOp` spans; `SYN*` (parse), `RUN*/ASN*/MOD*/CMP*/MTH*/IMP*/SHD*/WRN*`.
- Build: `bsharp build <file> [-o --output --keep-d --compiler]` →
  `driver.build_file` → emit `.d` → `[ldc2|dmd, .d, -of=exe]`.

## 3. AST coverage inventory and interpreter→backend mapping

Parser-constructible nodes (`nodes.py`), interpreter support, backend support:

| Node | Interpreter | Backend (`emitter.py`) |
|---|---|---|
| Number/Boolean/String/Char/None | full | NONE (only StringNode as 1-arg writeln payload) |
| NaN/Infinity | full | NONE |
| UnaryOp/BinaryOp (`is`≡`==` in worktree) | full incl. short-circuit, commit, CMP002/003 | NONE |
| CastNode | full (`convert_scalar`, String via render) | NONE |
| VariableAssign/MultiAssign/Reassign/Access | full (narrow/commit/copy) | NONE |
| IncrementNode | full (int-only, pre/post) | NONE |
| If/While/Do/For + Block | full (leak/body-scope/for-context rules) | NONE |
| FunctionDef/Call/Return | full (bind/defaults/recursion depth 500/closure/return checks) | NONE (any Call except 1-string writeln → error) |
| List/Tuple/Index/Slice/MethodCall | full (alias/copy/freeze/grow/drop rules) | NONE |
| StructDef/PropertyAccess/PropertyAssign | full | NONE |
| Import/TryCatch/Break/Continue/Pass | full | NONE |
| ContainerNode | NONE (`RUN001`, no visitor, no parser production) | NONE |

Emitter coverage: **~3/39 kinds** (`StatementsNode`, 1-string `__writeln`
`CallNode`, `StringNode`). All 5 `static_*.bsharp` fixtures → `BACKEND-ERROR`.

## 4. Existing backend capabilities and missing functionality

Capable today: emit `import std.stdio; void main(){writeln("…");}` for
`__writeln("literal")`-only programs; `driver.build_file` end-to-end to exe
when `ldc2/dmd` present; `--keep-d/-o/--compiler/BSHARP_D_COMPILER`.
Missing: §3 NONE column + `Backend/Runtime/` (0 files) + `main.d` (0 bytes) —
no D runtime for wrap/promote/precision/containers/strings/builtins/errors;
`__writeln` N-arg + 19 other builtins; pragmas; imports; `try/catch`; driver has
no timeout/cwd/mkdir/Runtime-sources/version-pin and writes `"(removed…)"`
string as `d_path`; `Tools/emit_d.py` no-arg guard + no `mkdir -p`;
`dump_ast.py` misses control/fn/struct fields + clobbers `codegen.d`.

## 5. Baseline test commands and actual results (2026-10-15)

All from repo root; compilers present (`/usr/bin/{ldc2,dmd,dub}`, py 3.12.3):

1. `python3 -m pytest Tests/ -q --ignore=Tests/test_number_fuzz.py -p no:cacheprovider`
   → **914 passed, 10 subtests passed in 13.14s**, exit 0.
2. `python3 -m pytest Tests/test_comparisons.py Tests/test_llvm_types.py Tests/test_syntax.py Tests/test_variables.py -q`
   → **119 passed in 0.46s**, exit 0.
3. `python3 Tests/golden_runner.py --check` → **All 15 golden program(s) match**, exit 0.
4. `python3 Tests/conformance_runner.py --check` → **All 26 conformance program(s) match**, exit 0.
5. `python3 -m pytest Tests/test_golden.py Tests/test_conformance.py -q` → **2 passed in 8.98s** (pytest gates healthy; earlier "import bug" report NOT reproduced).
6. `python3 Tests/D-Backend/diff_phase2.py` → **5 FAILURES**, exit 0 (harness exit is `1 if fails else 0` — observed `0` here is the `tail` pipeline's status; direct run returns 1):
   `static_vars/expr/control` → `BACKEND-ERROR: Unsupported VariableAssignNode`;
   `static_fn` → `Unsupported FunctionDefNode`; `static_struct` → `Unsupported StructDefNode`.
7. Minimal E2E (new probe): `__writeln("hello");` → `emit_d` wrote
   `/tmp/opencode/min_hello.d` (exit 0) → `ldc2 … -of=…_exe` → exe printed
   `hello`, exit 0. **Smallest reliable path confirmed.**
8. Negative probes: `__writeln("a","b")` → `BACKEND-ERROR: Function '__writeln' requires one argument`; `var x = 1;` → `BACKEND-ERROR: Unsupported VariableAssignNode` (both exit 2 from `emit_d.py`).
9. `Tests/test_number_fuzz.py` excluded from baseline (lengthy/threaded); to be run in Phase 1.

## 6. Differential harness assessment (`diff_phase2.py:1-75`)

Correct: per-fixture interp→build→exe→compare loop; exe 30s timeout; `ALL
PASS/n FAILURES` + `sys.exit(fails?1:0)` gate semantics; `--keep-d` + fixture
args. Deficiencies (documented, not fixed in Phase 0):
(a) compares **stdout only** (golden/conformance require stdout+stderr+exit);
(b) no timeout on interp/build (exe only; `TimeoutExpired` swallowed as generic
`EXE-SPAWN-ERROR` without partial output); (c) never compares exit codes beyond
both-zero path, no error-parity; (d) no `<ROOT>` normalization, no textual diff
(unlike golden `difflib`); (e) cleanup `for f in (exe, base+".d" if not keep
else exe)` redundant and never removes stale `*.o` (430–601KB ELF relocatables
committed in `Tests/D-Backend/`); (f) `.d "(removed…)"` sentinel breaks path
expectations. Verdict: adequate as Phase 1–4 red/green gate for stdout parity;
must be upgraded in Phase 6 (timeouts, triple-compare, diffs, artifact policy).

## 7. Known discrepancies, ambiguities, risks

See `TODO.md` "Known semantic discrepancies" (10 code-level + changelog/SDK/
`run`-subcommand divergences). Top backend risks: (1) D native ints/floats do
NOT replicate wrap/`to_f32`/promote/`Long+Float→Double`/NaN-unordered/`Bool`
coercion without a runtime; (2) commit-on-rest + render agreement must be
reimplemented in D; (3) alias/copy/freeze (`VariableAccess` alias,
`List/Array.copy` on store, const deep-freeze, `Tuple` immutability `RUN139`)
needs ownership design in D; (4) scoping leaks (`if` leaks, loop
`BodyScopeContext`, closure/import isolation) need emission strategy;
(5) `ContainerNode`/`ifdef` are spec holes in the interpreter itself —
clarify before emitting them.

## 8. Changes made, with reasons (Phase 0)

- Created `Processing/TODO.md` + `Processing/Phase_0.md` (required by Stage 2).
  No source, test, or backend modifications; no installs; no destructive ops.
- Probes lived in `/tmp/opencode/` only (`min_hello`, `probe_multi`, `probe_var`).
- Pre-existing uncommitted changes (`is` keyword, `main()`+130) inspected via
  `git diff`, recorded in `TODO.md`, and **preserved** — Phase 0 authors no
  colored diffs to them. `test.bsharp` (previously untracked) no longer present;
  recorded as absent, not restored.

## 9. Tests executed after every implementation step

Phase 0 steps were docs + read-only probes; after each probe group the narrow
relevant check was re-run: emitter probes → `emit_d` exit/message; E2E probe →
exe output/exit; harness probe → full `diff_phase2` output; suite probe → full
`pytest` (914) + golden (15) + conformance (26). No regressions possible (no
source edits); results in §5 are the recorded baseline for Phase 1 comparison.

## 10. Final acceptance checklist, blockers, Phase 1 proposal

Gate (all must hold — they do): [x] audit documented (§1–§3); [x] inventory
grounded in source (file:line refs throughout); [x] AST map complete (§3);
[x] baseline recorded with commands+counts (§5); [x] harness validated /
limitations documented (§6); [x] architecture + invariants explicit (§2 + §7);
[x] roadmap with dependencies + measurable criteria (`TODO.md` phases);
[x] changes + results in both docs (§8–§9); [x] next phase ready without
foundational questions.

Blockers: none. Note: commit the pre-existing `is` + `bsharp.py main()`
work on its own branch/commit before Phase 1 so backend diffs stay separable;
decide `ContainerNode`/`ifdef` disposition during Phase 1 design (spec first).

Proposed Phase 1 scope (from `TODO.md`, acceptance = `static_vars` +
`static_expr` green in `diff_phase2` + covered `test_llvm_types` pins):
literals, arithmetic/comparison/logic + short-circuit, typed `var/const` +
reassign + `++/--`, `__writeln` N-arg parity, and the seed `Backend/Runtime/`
(render/wrap/promote/precision) it depends on. Do NOT start Phase 1 until
explicit approval — stopping at the gate per instructions.
