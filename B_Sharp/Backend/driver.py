"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

The main driver for D-Language Transpilation from B-Sharp.
This module finds the suited D-Compiler, builds the file, and returns the executable's
path in addition to the transpiled D-language file path.
"""

import os
import shutil
import subprocess

from B_Sharp.frontend import parse_source
from B_Sharp.Backend.emitter import DLanguageEmitter, DBackendError


class BuildError(Exception):
    pass


def find_d_compiler(hint=None):
    env = os.environ.get("BSHARP_D_COMPILER")
    for cand in (hint, env, "ldc2", "dmd"):
        if cand and shutil.which(cand):
            return cand
    raise BuildError("no D compiler found (tried ldc2, dmd). Install ldc + dub.")


def build_file(source_path, output_path=None, keep_d=False, compiler=None):
    if not source_path.endswith(".bsharp"):
        raise BuildError("source must end with .bsharp")
    if not os.path.exists(source_path):
        raise BuildError(f"file '{source_path}' does not exist")

    with open(source_path, "r", encoding="utf-8-sig") as f:
        src = f.read()

    res = parse_source(source_path, src)
    if res.has_error:
        raise BuildError(str(res.error))

    try:
        dcode = DLanguageEmitter().emit(res.ast_root)
    except DBackendError as e:
        raise BuildError(f"BACKEND-ERROR: {e}")

    base, _ = os.path.splitext(source_path)
    d_path = base + ".d"
    exe_path = output_path or base

    with open(d_path, "w", encoding="utf-8") as f:
        f.write(dcode)

    comp = find_d_compiler(compiler)

    cmd = [comp, d_path, f"-of={exe_path}"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise BuildError(f"{comp} failed:\n{proc.stdout}\n{proc.stderr}")

    if not keep_d:
        try:
            os.remove(d_path)
        except OSError:
            pass
        d_path = "(removed, use --keep-d to keep)"

    return exe_path, d_path
