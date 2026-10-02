# Changelog

B-Sharp is still in version 0.0.1. Changelogs are comming soon.

## 0.2.0 – LLVM-driven types (interpreter route)

- Replaced `Number` with fixed-width numerics: `Short` (i8), `Single`
  (i16), `Integer` (i32), `Long` (i64), `Float` (f32), `Double` (f64).
  Integer arithmetic wraps two's-complement; `/` on ints yields Double.
- Split strings: double-quoted `String` vs single-quoted `Char`
  (exactly one character). String indexing yields `Char`.
- New single source of truth: `B_Sharp/typesys.py` (widths, LLVM types,
  promotion, wrapping, literal rules) shared by the interpreter and the
  future compiler backend.
- Literals default to Long/Double with `L/i/s/b/f/D` suffixes;
  kind-strict narrowing: int literals only into int types, float
  literals only into float types — cross-kind literals are ASN005
  (RUN123 at return positions). New `cast(value, Type)` conversion form.
- `!pragma enforce` now rejects unannotated first parameters (SYN076);
  previously only later parameters were checked.
- `!pragma precision N` quantizes values coming to rest: arithmetic
  runs at full precision, but a value that is stored, returned, bound,
  compared, tested or displayed carries exactly N decimals — store and
  show always agree. So `1.0/3.0*3.0` computes to `1.0`, stores `1.0`
  and shows `1.00`; `0.1 + 0.2` stores `0.3` and
  `(0.1 + 0.2) == 0.3` is true (per-file config, never leaking across
  imports). This is deliberate language design: the wanted precision
  governs the value itself, not just its display.
- Renamed builtins: `__is_Numeric` (+ per-type `__is_Long`…), `__is_Char`,
  `__to_Long` / `__to_Double` (replacing `__is_Number` / `__to_Number`).
- Hard break, no aliases. Golden + conformance baselines re-recorded;
  `bsharp build` (compiler route) intentionally left unimplemented.

## Unreleased – LLVM-readiness blockers BL-1…BL-4

- BL-1: loop headers now handle `break`/`continue`/`return` instead of
  crashing on a `None` condition (`for` init/condition/update and
  `while` condition). A flag binds to the innermost loop whose context
  validated it; `return` always propagates. `do-while` behavior
  unchanged (it was already the model).
- BL-2: precision commits are now pure — container commits rebuild
  fresh containers with freshly committed elements, so committing can
  no longer rewrite the committed-from object (`Tuple.copy()` returns
  a real copy; `Float` elements and bare `Float`s narrow to binary32
  uniformly). Importing a name is a rest point quantized under the
  importer's precision config; an importer's commits never touch the
  module's stored objects. New pins: input-immutability unit test, an
  import-truthiness pin (`check(0.049)` → `0` at precision 1), and a
  three-file cross-precision alias pin (prints `1.2346`, not `1.2000`).
- BL-3: `typesys` table corrected — `Char` is `i32` (full code point),
  `String` lowers to UTF-32 code units, `NaN`/`Inf` are tagged
  singletons (`ptr`), never `double`. No behavior change (fields were
  dead); new pins lock code-point semantics
  (`cast('é', Integer) == 233`, `"héllo→world".length == 11`).
- BL-4: module diagnostic timing frozen and pinned
  (`Tests/test_module_timing.py`): missing module → RUN026 at parse
  time (uncatchable, exit 2); bad module → catchable at import
  execution (uncaught → exit 2). No interpreter change.
- BL-5 (`[#ifdef]` parser crash) intentionally left untouched.