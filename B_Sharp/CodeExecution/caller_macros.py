# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# The code is guarded and licensed under the GPLv3 License.
# --------------------------------------------------------------
# Module: caller_macros.py: Per-file configuration driven by
# `!pragma` caller macros.

from dataclasses import dataclass
from typing import Optional

from B_Sharp.tokens import (
    TOKEN_INT,
    TOKEN_EOF,
    TOKEN_MACRO,
    TOKEN_NEWLINE,
    TOKEN_SEMICOLON,
    TOKEN_IDENTIFIER,
)
from B_Sharp.Errors.errors import B_SharpSyntaxError

MACROS = ("pragma",)
DIRECTIVE_ARGS = {
    "enforce": None,
    "precision": "number",
}

MIN_PRECISION = 0
MAX_PRECISION = 18
REPL_FILE_NAME = "<stdin>"


@dataclass(frozen=True)
class FileConfig:
    """
    Settings collected from the leading caller macros.

    Each source file owns its own config: an importer's macros never
    affect an imported module, and vice-versa.
    """

    enforce_types: bool = False
    precision: Optional[int] = None
    optimize: bool = False


DEFAULT_CONFIG = FileConfig()

# Registry keyed by the exact string that every node already carries in
# `Position.file_name`. Sole purpose: runtime lookups (rounding + display).
_FILE_CONFIGS = {}


def get_config(file_name):
    """Return the config of a file (default when unknown/tokenless)."""
    if file_name is None:
        return DEFAULT_CONFIG
    return _FILE_CONFIGS.get(file_name, DEFAULT_CONFIG)


def register_config(file_name, cfg):
    _FILE_CONFIGS[file_name] = cfg


def _is_separator(token):
    return token.type in (TOKEN_NEWLINE, TOKEN_SEMICOLON, TOKEN_EOF)


def preprocess_pragmas(tokens, file_name):
    """
    Strip the leading `!pragma` lines off a token stream.

    Applies the declarations to the file's own `FileConfig` and returns
    `(clean_tokens, cfg, error)`. Nothing is registered on failure.
    """
    n = len(tokens)
    i = 0

    while i < n and tokens[i].type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
        i += 1

    # REPL lines merge into the session's existing "<stdin>" config so a
    # later line without pragmas keeps the earlier settings. Real files
    # always rebuild a fresh config from their own text.
    if file_name == REPL_FILE_NAME:
        cfg = _FILE_CONFIGS.get(file_name, DEFAULT_CONFIG)
    else:
        cfg = FileConfig()

    if i < n and tokens[i].type != TOKEN_MACRO:
        register_config(file_name, cfg)
        return tokens, cfg, None

    while i < n and tokens[i].type == TOKEN_MACRO:
        macro_tok = tokens[i]
        i += 1

        directive_tok = tokens[i] if i < n else None
        if directive_tok is None or directive_tok.type not in (
            TOKEN_IDENTIFIER,
            TOKEN_MACRO,
        ):
            return (
                tokens,
                cfg,
                B_SharpSyntaxError(
                    macro_tok.pos_start,
                    macro_tok.pos_end,
                    "SYN068",
                ),
            )

        directive = directive_tok.value
        i += 1

        if directive == "enforce":
            if i >= n or not _is_separator(tokens[i]):
                return (
                    tokens,
                    cfg,
                    B_SharpSyntaxError(
                        directive_tok.pos_start,
                        directive_tok.pos_end,
                        "SYN079",
                        {"name": "enforce"},
                    ),
                )
            cfg = FileConfig(enforce_types=True, precision=cfg.precision)
        elif directive == "precision":
            arg_tok = tokens[i] if i < n else None
            if arg_tok is not None and arg_tok.type == TOKEN_IDENTIFIER:
                if arg_tok.value == "default":
                    cfg = FileConfig(enforce_types=cfg.enforce_types, precision=None)
                    i += 1
                else:
                    return (
                        tokens,
                        cfg,
                        B_SharpSyntaxError(
                            arg_tok.pos_start,
                            arg_tok.pos_end,
                            "SYN078",
                        ),
                    )
            elif arg_tok is not None and arg_tok.type == TOKEN_INT:
                if MIN_PRECISION <= arg_tok.value <= MAX_PRECISION:
                    cfg = FileConfig(
                        enforce_types=cfg.enforce_types,
                        precision=arg_tok.value,
                    )
                    i += 1
                else:
                    return (
                        tokens,
                        cfg,
                        B_SharpSyntaxError(
                            arg_tok.pos_start,
                            arg_tok.pos_end,
                            "SYN078",
                        ),
                    )
            else:
                return (
                    tokens,
                    cfg,
                    B_SharpSyntaxError(
                        directive_tok.pos_start,
                        directive_tok.pos_end,
                        "SYN078",
                    ),
                )
            if i >= n or not _is_separator(tokens[i]):
                return (
                    tokens,
                    cfg,
                    B_SharpSyntaxError(
                        arg_tok.pos_start,
                        arg_tok.pos_end,
                        "SYN078",
                    ),
                )
        else:
            return (
                tokens,
                cfg,
                B_SharpSyntaxError(
                    directive_tok.pos_start,
                    directive_tok.pos_end,
                    "SYN080",
                    {"name": directive},
                ),
            )

        while i < n and tokens[i].type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
            i += 1

    register_config(file_name, cfg)
    return tokens[i:], cfg, None


def round_number(raw, cfg):
    """Round a raw Python number according to a config (floats only)."""
    if cfg.precision is None:
        return raw
    if type(raw) is float:
        return round(raw, cfg.precision)
    return raw


def round_result(value, cfg):
    """Round a runtime value tree (Number / List / Array / Tuple) in place."""
    if cfg.precision is None:
        return value

    from B_Sharp.ASTNodes.instances import Number, List, Array, Tuple

    if isinstance(value, Number):
        if type(value.value) is float:
            value.value = round(value.value, cfg.precision)
        return value
    if isinstance(value, Tuple):
        for idx, element in enumerate(value.elements):
            value.elements[idx] = round_result(element, cfg)
        return value
    if isinstance(value, (List, Array)):
        for idx, element in enumerate(value.list_of_elements):
            value.list_of_elements[idx] = round_result(element, cfg)
    return value


def render_element(value, cfg):
    """Render one element the way it appears nested inside a list/array."""
    from B_Sharp.ASTNodes.instances import Number, List, Array, Tuple

    if isinstance(value, Tuple):
        inner = ", ".join(render_element(e, cfg) for e in value.elements)
        return f"({inner})"
    if isinstance(value, (List, Array)):
        inner = ", ".join(render_element(e, cfg) for e in value.list_of_elements)
        return f"[{inner}]"
    if isinstance(value, Number):
        if cfg.precision is not None:
            return f"{value.value:.{cfg.precision}f}"
        return repr(value)
    return repr(value)


def render_value(value, cfg):
    """
    Render a top-level value for display (writeln / to_String / REPL).

    Mirrors the historical behaviour exactly whenever no precision is set:
    top-level strings are unquoted, error instances show their formatted
    message, everything else uses str/repr. With a precision set, every
    number renders with exactly that many decimal places.
    """
    from B_Sharp.ASTNodes.instances import (
        List,
        Array,
        String,
        Number,
        Tuple,
        ErrorInstance,
    )

    if isinstance(value, String):
        return value.value
    if isinstance(value, ErrorInstance):
        try:
            if hasattr(value.error, "as_string"):
                return value.error.as_string()
            return str(value)
        except Exception:
            return str(value)
    if isinstance(value, Number):
        if cfg.precision is not None:
            return f"{value.value:.{cfg.precision}f}"
        return str(value)
    if isinstance(value, (List, Array)):
        if cfg.precision is None:
            return str(value)
        inner = ", ".join(render_element(e, cfg) for e in value.list_of_elements)
        return f"[{inner}]"
    if isinstance(value, Tuple):
        if cfg.precision is None:
            return str(value)
        inner = ", ".join(render_element(e, cfg) for e in value.elements)
        return f"({inner})"
    return str(value)
