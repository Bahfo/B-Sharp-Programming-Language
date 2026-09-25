import time
import sys
import os

from B_Sharp.frontend import parse_source
from B_Sharp.ASTNodes.instances import Context
from B_Sharp.builtins import register_builtins
from B_Sharp.ASTNodes.interpreter import Interpreter
from B_Sharp.Compiler.driver import CompilerDriver, CompileOptions
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

    if context is None:
        context = Context("<main>")
        register_builtins(context)

    # Unified Frontend Call
    frontend_res = parse_source(file_name, source_text)
    if frontend_res.has_error:
        return None, frontend_res.error, None

    interpreter = Interpreter()
    result = interpreter.visit(frontend_res.ast_root, context)
    if result.error:
        return None, result.error, None

    elapsed_time = (time.perf_counter() - start_time) if measure_time else None
    return result.value, None, elapsed_time


def compile_file(file_path, options: CompileOptions):
    """
    Compiles a .bsharp source file to a standalone native binary via B# LLVM Compiler.
    """
    if not file_path.endswith(".bsharp"):
        print(
            "Error: Invalid file extension. B_Sharp compiler requires '.bsharp' files."
        )
        sys.exit(1)

    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source_text = f.read()
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)

    frontend_res = parse_source(file_path, source_text)
    if frontend_res.has_error:
        print(frontend_res.error)
        sys.exit(1)

    driver = CompilerDriver(file_path, options)
    success = driver.compile(frontend_res.ast_root, frontend_res.file_config)
    if not success:
        sys.exit(1)


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
        with open(file_path, "r", encoding="utf-8") as f:
            source_text = f.read()
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        sys.exit(1)

    value, error, elapsed_time = run_source(
        file_path, source_text, measure_time=measure_time
    )

    if error:
        print(error)
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
    print("  bsharp                           Start REPL")
    print("  bsharp <file.bsharp>              Interpret file")
    print("  bsharp build <file.bsharp> [opts] Compile file to native executable")
    print("\nCompiler Options:")
    print("  -o <path>                        Specify output executable path")
    print("  --emit-llvm                      Emit compiled LLVM IR file (.ll)")
    print("  --emit-c                         Emit translated C source file (.c)")


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
        options = CompileOptions()

        i = 2
        while i < len(args):
            if args[i] == "-o" and i + 1 < len(args):
                options.output_path = args[i + 1]
                i += 2
            elif args[i] == "--emit-llvm":
                options.emit_llvm = True
                i += 1
            elif args[i] == "--emit-c":
                options.emit_c = True
                i += 1
            else:
                print(f"Unknown compiler option: {args[i]}")
                sys.exit(1)

        compile_file(source_file, options)
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
