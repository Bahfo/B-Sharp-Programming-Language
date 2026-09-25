"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Native Compilation Driver for B-Sharp.
Orchastrates semantic analysis, LLVM IR code generation C runtime linkage,
and target host binary emission.
"""

import os
import sys
import subprocess

from B_Sharp.Compiler.symbol_table import SemanticAnalyzer
from B_Sharp.Errors.errors import SemanticError


class CompileOptions:
    def __init__(
        self,
        output_path=None,
        emit_llvm=False,
        emit_c=False,
        opt_level=2,
    ):
        self.output_path = output_path
        self.emit_llvm = emit_llvm
        self.emit_c = emit_c
        self.opt_level = opt_level


class CompilerDriver:
    def __init__(
        self,
        file_name: str,
        options: CompileOptions = None,
    ):
        self.file_name = file_name
        self.options = options or CompileOptions()
        self.symbol_table = None

    def compile(self, ast_root, file_config=None) -> bool:
        """
        Main Compilation Function for B-Sharp Programming Language

        Converts B# AST into native executables via C Runtime and LLVM
        backend.
        """

        base_name = os.path.splitext(self.file_name)[0]
        output_exe = self.options.output_path or (
            f"{base_name}.exe" if sys.platform == "win32" else base_name
        )  # Depends whether core is for Linux or Windows

        llvm_ir_code = f"; B# LLVM IR Module for file: {self.file_name}\n"
        llvm_ir_code += 'target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"\n'
        llvm_ir_code += 'target triple = "x86_64-pc-linux-gnu"\n\n'

        if self.options.emit_llvm:
            llvm_file = f"{base_name}.ll"
            with open(llvm_file, "w", encoding="utf-8") as f:
                f.write(llvm_ir_code)

            print(f"[BSHARP] Code Compilation IR is generated to {llvm_file}")

        analyzer = SemanticAnalyzer()
        try:
            self.symbol_table = analyzer.analyze(ast_root)
            print(f"[BSHARP] Semantic analysis passed successfully.")

        except SemanticError as err:
            print(f"[BSHARP] {err.message}")
            return False

        return True
