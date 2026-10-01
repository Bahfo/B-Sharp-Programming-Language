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
- Literals default to Long/Double with `L/i/s/b/f/D` suffixes; numeric
  literals narrow into annotated positions when exactly convertible,
  otherwise ASN005. New `cast(value, Type)` conversion form.
- Renamed builtins: `__is_Numeric` (+ per-type `__is_Long`…), `__is_Char`,
  `__to_Long` / `__to_Double` (replacing `__is_Number` / `__to_Number`).
- Hard break, no aliases. Golden + conformance baselines re-recorded;
  `bsharp build` (compiler route) intentionally left unimplemented.