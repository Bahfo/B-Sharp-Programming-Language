# Main Entrance for the B-Sharp Programming Language
# Once compiled, the program becomes a standalone executable. In other
# terms, it can be called as: `bsharp run ...` or `bsharp build ...`

# Written by Bahaa Nofal

import time
import sys
import os

from B_Sharp.frontend import parse_source
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.builtins import register_builtins
from B_Sharp.ASTNodes.interpreter import Interpreter
from B_Sharp.CodeExecution.caller_macros import (
    get_config,
    render_value,
)


def run_source(file_name, source_text, context=None, measure_time=False):
    """
    Executes B_Sharp source text through frontend parser and AST Interpreter.
    Always returns a 3-tuple: (value, error, elapsed_time)
    """
    start_time = time.perf_counter()

    if source_text.startswith("\ufeff"):
        source_text = source_text[1:]

    if context is None:
        context = Context("<main>")
        register_builtins(context)

    frontend_res = parse_source(file_name, source_text)
    if frontend_res.has_error:
        frontend_res.error.phase = "frontend"
        return None, frontend_res.error, None

    interpreter = Interpreter()
    result = interpreter.visit(frontend_res.ast_root, context)
    if result.error:
        if not getattr(result.error, "phase", None):
            result.error.phase = "runtime"
        return None, result.error, None

    elapsed_time = (time.perf_counter() - start_time) if measure_time else None
    return result.value, None, elapsed_time


def run_file(file_path, measure_time=False):
    """
    Validates and interprets a .bsharp file.
    """
    if not file_path.endswith(".bsharp"):
        print("Error: Invalid file extension. B_Sharp runner supports '.bsharp' files.")
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            source_text = f.read()
    except UnicodeDecodeError:
        print(f"Error reading file '{file_path}': not valid UTF-8 text.")
        sys.exit(2)
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)

    value, error, elapsed_time = run_source(
        file_path, source_text, measure_time=measure_time
    )

    if error:
        print(error)
        sys.exit(2 if getattr(error, "phase", "runtime") == "frontend" else 1)
    elif value is not None and repr(value) != "none":
        print(render_value(value, get_config(file_path)))

    if elapsed_time is not None:
        print(f"Measured runtime: {elapsed_time:.6f}s")


def run_repl():
    """
    Interactive Command Line REPL for B_Sharp.
    """
    print("B_Sharp Language REPL v1.0 [Dynamic Interpreter / Compiler Driver]")
    print("Type 'exit()','quit()' or press Ctrl+C to exit.\n")

    global_context = Context("<main>")
    register_builtins(global_context)

    while True:
        try:
            line = input("bsharp> ")
            if line.strip() in ("exit()", "quit()"):
                break
            if not line.strip():
                continue

            value, error, _ = run_source("<stdin>", line, global_context)

            if error:
                print(error)
            elif value is not None and repr(value) != "none":
                print(render_value(value, get_config("<stdin>")))

        except (KeyboardInterrupt, EOFError):
            print("\nExiting B_Sharp.")
            break


def print_usage():
    print("Usage:")
    print("  bsharp                             Start REPL")
    print("  bsharp run <file.bsharp>           Interpret file")
    print("  bsharp build <file.bsharp> [opts]  Compile file to native executable")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        run_repl()
    elif args[0] == "build" or args[0] == "compile":
        if len(args) < 2:
            print("Error: No input source file provided for compilation.")
            print_usage()
            sys.exit(1)

        source_file = args[1]
    else:
        measure_time = False
        if "--measure" in args:
            measure_time = True
            args.remove("--measure")
        elif "-m" in args:
            measure_time = True
            args.remove("-m")

        if args:
            run_file(args[0], measure_time=measure_time)
        else:
            print("Error: No file specified.")
            sys.exit(1)
