# B-Sharp Project
## *The B-Sharp Programming Language Official Source Code*

This repository contains the source code for the B-Sharp Programming Language.

## Table of Contents
1. Getting Started.
2. Using B-Sharp.
3. Repository Layout.

## Getting Started
Welcome to the official repository for the B-Sharp Programming Language!

B-Sharp (or B# simply) aims to be a syntax-clean language that is simple to learn, and still covers everything a scripted language should:
- An easy-to-learn syntax that does not get in your way.
- A standard library with math, complex math, and standard input/output.
- Support inside DreamStudio, plus plugins for VSCode and NeoVim.
- A syntax that looks familiar, with extra features such as caller macros and type enforcement.

B# can be interpreted today. Compilation is being rebuilt, so the interpreter is what you use for now.

## Using B-Sharp
Everything runs straight from the source code. No setup needed:

```bash
# Run a file
python3 bsharp.py example.bsharp

# Run it and print the runtime
python3 bsharp.py example.bsharp --measure

# Start the REPL
python3 bsharp.py
```

A hello world program in B# is simply written as:

```
__writeln("Hello World")
```

### Starting a Project
The SDK shell (written in D, inside `SDK/`) helps you manage projects:

```
bsharp init <project_name>   # create a new project
bsharp run start.bsharp      # run the project main file
bsharp help                  # show the help document
```

`bsharp install` and `bsharp uninstall` are announced but not implemented yet.

## Repository Layout
- `B_Sharp/`: the language implementation (lexer, parser, interpreter, builtins).
- `StdLib/`: the standard library. Today it ships `StdIO` and `StdMath` (real and complex).
- `Docs/`: the documentation, written chapter by chapter.
- `Examples/`: example programs, from getting started to complete ones.
- `SDK/`: the SDK shell and its utilities.
- `Plugins/`: language support for VSCode, NeoVim, and DreamStudio.
- `Tests/`: the test suite.

