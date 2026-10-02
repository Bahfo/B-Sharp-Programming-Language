# BSharp Language Support

Syntax highlighting and keyword/type awareness for the B-Sharp Programming
Language (`.bsharp` and `.bshead` files).

## Features

- Syntax highlighting for B# source files
- Single-line (`//`) and block (`/* ... */`) comments
- Double-quoted strings with escape sequences, single-quoted `Char` literals
- Keywords: control flow (`if`/`elif`/`else`/`then`/`do`/`for`/`while`/`try`/`catch`/`using`/`return`/`break`/`continue`/`pass`), function declarations (`fn`/`function`), storage (`var`/`const`/`struct`), logic (`and`/`or`/`not`)
- Types: `Bool`, `Short`, `Single`, `Integer`, `Long`, `Float`, `Double`, `Char`, `String`, `Empty`, `List`, `Tuple`, `Function`, `Inf`, `NaN`
- Array annotations: `Short[]`, `Single[]`, `Integer[]`, `Long[]`, `Float[]`, `Double[]`, `Char[]`, `String[]`, `Bool[]`, `Empty[]` (repeatable for nesting, e.g. `Long[][]`), plus `Tuple(...)` annotations
- Caller macros: `!pragma enforce`, `!pragma precision <0..12>`, `!pragma precision default` (stray `!name` / bare `!` flagged illegal; `!=` stays a comparison)
- Preproc blocks: `[#ifver]`, `[#ifdef]`, `[#define]`, `[#endif]` and platform constants `__GNU_LINUX`, `__NT_KERNEL`, `__DARWIN`
- `cast(value, Type)` conversion form (`Short`/`Single`/`Integer`/`Long`/`Float`/`Double`/`Char`/`String`/`Bool`)
- Error types used in `catch(...)` blocks (`Error`, `B_SharpSyntaxError`, `RunTimeError`, `AssignmentError`, `ModificationError`, `ComparisonError`, `BSharpMathError`, `ShadowingError`)
- Builtin functions (`__writeln`, `__write`, `__format`, `__read`, `__readln`, `__is_String`, `__is_Char`, `__is_Numeric`, `__is_Short`, `__is_Single`, `__is_Integer`, `__is_Long`, `__is_Float`, `__is_Double`, `__is_Empty`, `__is_Bool`, `__to_Long`, `__to_Double`, `__to_String`, `__time__`)
- Numbers, floats, scientific notation, and literal suffixes (`5i`/`5s`/`5b`/`5L`/`1.5f`/`5.0D`)
- Operators as the lexer defines them: `++`, `--`, `->`, `^` (power), `*`, `/`, `%` (integer division), `~` (modulo), `+`, `-`, `=`/`==`/`!=`/`<`/`>`/`<=`/`>=`, `.`/`..`/`...` (note: `**` is illegal and flagged)
- Autocompletion snippets (`snippets/bsharp.json`) for keywords, types, array types, all `__` builtins, `!pragma` macros, `[#...]` preproc blocks, `cast(value, Type)`, and `catch(...)` error types — with tab-stop templates for `fn`, `if`/`for`/`while`/`try`, and `var`/`const`

## Installing Locally (development)

Package and install into your local VSCode instance (no marketplace
publishing involved):

```bash
cd Plugins/VSCode/bsharp-language-support
npm install -g @vscode/vsce   # once, if `vsce` is not already available
npm run compile               # builds out/bsharp-language-support-<version>.vsix
npm run install               # code --install-extension out/*.vsix --force
```

> **Node 20+**: recent `@vscode/vsce` releases require Node >= 20. If your
> default `node` is older (e.g. 18), run vsce with a newer Node directly,
> e.g.:
> ```bash
> ~/.nvm/versions/node/v20.20.2/bin/node /home/bahaa/.npm-global/bin/vsce \
>   package --allow-missing-repository --out out/
> ```

Or manually, with the Extension Development Host (most useful while
iterating on the grammar):

1. Open this folder in VSCode.
2. Press `F5` (uses `.vscode/launch.json`).
3. A new window opens with the extension loaded; open a `.bsharp` file to
   test the highlighting live.

## Grammar layout

- `syntaxes/bsharp.tmLanguage.json` — the TextMate grammar (single source of
  truth for highlighting).
- `snippets/bsharp.json` — autocompletion snippets; registered via the
  `snippets` contribution in `package.json`.
- `language-configuration.json` — comments, brackets, auto-closing pairs.
- `package.json` — extension manifest; bump `version` before repackaging.

The grammar mirrors `B_Sharp/tokens.py` (keywords/types), `B_Sharp/lexer.py`
(operators/comments/strings/chars/macros), `B_Sharp/builtins.py` (builtin
names), `B_Sharp/typesys.py` + `B_Sharp/ASTNodes/instances.py` (valid type and
array spellings, `cast` targets) and `B_Sharp/CodeExecution/caller_macros.py`
(`!pragma` directives): keep `syntaxes/bsharp.tmLanguage.json` in sync
whenever tokens or caller macros change.
