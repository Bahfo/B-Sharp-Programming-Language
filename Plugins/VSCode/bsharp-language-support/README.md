# BSharp Language Support

Syntax highlighting and keyword/type awareness for the B-Sharp Programming
Language (`.bsharp` and `.bshead` files).

## Features

- Syntax highlighting for B# source files
- Single-line (`//`) and block (`/* ... */`) comments
- Double- and single-quoted strings with escape sequences
- Keywords: control flow, function/type declarations, storage (`var`/`const`/`struct`)
- Types: `Number`, `String`, `Bool`/`Boolean`, `List`, `Function`, `Inf`, `NaN`, `Empty`
- Array annotations: `Number[]`, `String[]`, `Bool[]`, `Empty[]`, ...
- Caller macros: `!pragma enforce`, `!pragma precision <0..12>`, `!pragma precision default`
- Error types used in `catch(...)` blocks
- Builtin functions (`writeln`, `write`, `format`, `read`, `readln`, `to_String`, ...)
- Numbers, floats, and scientific notation

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
- `language-configuration.json` — comments, brackets, auto-closing pairs.
- `package.json` — extension manifest; bump `version` before repackaging.

The grammar mirrors `B_Sharp/tokens.py`: keep the keyword list in
`syntaxes/bsharp.tmLanguage.json` in sync whenever new keywords or caller
macros are added to the language.