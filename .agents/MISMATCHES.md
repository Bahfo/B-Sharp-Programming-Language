# Mismatches — grammar vs. implementation vs. tests

Recorded, not concealed. Each entry: what diverges, where, and the
standing decision. `Grammar/` is descriptive: the implementation wins
every conflict below until the owner rules otherwise.

## M-LEX-1 — `...` emits two tokens (accepted quirk, in grammar)

`lexer.py:401-413`: the `...` branch emits `ELLIPSIS` and then falls
through into the `..` branch, emitting `DOTDOT` as well. The grammar
records both emissions; `ELLIPSIS` has no parser role (any expression
use fails `SYN034`, cf. Findings probe `M05a`). Fix = add the missing
`else`; until then the grammar describes the double emission.

## M-LEX-2 — Dead caller-macro names (accepted, in grammar)

`tokens.py` lists `panic`/`allow`/`remember` as caller macros and the
lexer accepts all four `!name` spellings, but `preprocess_pragmas`
implements only `pragma` directives — the other three always fail
(`SYN080`, or `SYN068` bare). The grammar lists them as lexable but
without accepted directives. Same standing as Findings `P06` (BUG).

## M-LEX-3 — `%` is IDIV, `~` is MODULO (accepted, in grammar)

Token names contradict their characters (`%` = integer division,
`~` = remainder). The grammar maps characters faithfully and notes the
naming. Renaming tokens would churn the whole codebase; not proposed.

## M-PP-1 — `[#ifdef]` crashes the parser (BUG, in grammar as rejected)

The lexer accepts `[#ifdef]`, but `Parser._pass()` (parser.py:1209) is
an unimplemented stub (`print("Hi")`, returns `None`) that crashes
statement parsing with `AttributeError`. The grammar documents only
`[#ifver]`/`[#endif]` as accepted; `ifdef`/`define` are lexable but have
no working syntax. Same standing as Findings `M03` (BUG).

## M-PP-2 — Optional `]` after `[#ifver` (accepted, in grammar)

`lexer.py:519-520`: a missing `]` still emits the PREPROC token. The
grammar marks the bracket optional to match. Strictness is an owner
call (Findings SMELL).

## M-SYN-1 — Container placement is not context-free (accepted, §11 C1)

`container_def` parses identically everywhere; legality depends on the
parser's runtime `block_depth`. The grammar rule over-accepts and §11
carries the real rule. Verified by `test_containers.py` placement
tests (`SYN088` in fn/if/while/for).

## M-SYN-2 — `self` validity is runtime-only (accepted, §11 C2)

The grammar accepts `self` in any atom position; legality (init or
owned method) is enforced by the interpreter (`RUN149`/`RUN150`).
Verified by `test_containers.py` (`test_self_outside_rejected`,
`test_self_as_value_rejected`, `test_nested_function_hides_self`).

## M-SYN-3 — Enforce mode changes the language (accepted, §11 C3)

`!pragma enforce` adds `SYN075/076/077` restrictions (mandatory
annotations incl. `for`-counters). The grammar shows the enforce-off
accept set. Verified by `Tests/test_pragmas.py:20-102`.

## M-SYN-4 — Trailing-comma asymmetry (accepted, documented)

Tolerated: list literals, tuple literals/groupings, `return a, b,`.
Rejected: call arguments, parameter lists. Each rule states its own
policy because the implementation does not share one. No test pins
the call/param rejection explicitly (GAP — suggested corpus probes).

## M-SYN-5 — `using` symbols live inside the string (accepted)

`using "path:sym1,sym2"` — selection is string content split on
`":"` then `","`, not grammar tokens. The grammar shows the string
form with a note. Verified by `test_imports.bsharp` selective imports.

## M-SYN-6 — `cast` is contextual, not a keyword (accepted)

`cast` is an ordinary identifier that becomes a conversion only when
immediately followed by `(`. A variable named `cast` used otherwise
parses as a variable. In grammar via the atom alternative + note.

## M-SYN-7 — Statement separation edge rules (accepted)

(a) `return a, b` tuples are single-line-only; (b) a statement may
follow `}` with no separator; (c) `var x = var y = …` chains while
`x = y = …` does not parse. All three verified against
`statements()`/`return_statement()`/`var_decl()`; (a) and (b) are
covered by `test_syntax.py` separator tests.

## M-DOC-1 — `Docs/list of keywords.md` is an empty table

The docs promise a keyword list but contain only blank rows. The
authoritative lists live in `tokens.py:85-153` and are reproduced in
`Lexical.grammar`. Docs fix, not a language issue.

## M-TEST-1 — Audit vs. parser test cases (checked 2026-10-16)

- Valid cases sampled: `test_syntax.py` (precedence, separators,
  if/while/for `then` forms, increments), `test_control_flow.bsharp`
  (all loop/if shapes), `test_functions.bsharp`, `Tests/ast/snippets`
  — all parse under this grammar. No valid-case contradiction found.
- Invalid cases sampled: unterminated string (`SYN003`), missing
  `for` semicolons (`SYN048/049`), bad string multiplication (a
  *runtime* `RUN099`, correctly absent from syntax rules) — all
  consistent with the grammar's accept set and error annotations.
- One test-name overclaim (not a grammar issue): tests named
  `…_fails` for const reassignment exercise runtime `MOD002`, which
  the grammar correctly does not model (assignment shape is accepted;
  constness is semantic).
- GAP: call-argument and parameter-list trailing-comma rejections have
  no dedicated invalid-case tests; like `M-SYN-4`, suggested probes.
