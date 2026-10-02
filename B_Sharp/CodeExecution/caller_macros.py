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

CALLER_MACROS = ("pragma",)
DIRECTIVE_ARGS = {
    "enforce": None,
    "precision": "number",
}

MIN_PRECISION = 0
MAX_PRECISION = 12
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


def _quantize_numeric(value, cfg):
    """Return a FRESH numeric value quantized to ``cfg.precision`` decimals.

    Float results are additionally narrowed to binary32, matching the
    interpreter's per-op Float rule. The input object is never touched.
    """
    payload = value.value
    if type(payload) is float:
        payload = round(payload, cfg.precision)
    out = type(value)(payload)
    if out.type_name == "Float":
        from B_Sharp import typesys as _ts

        out.value = _ts.to_f32(out.value)
    return out


def round_result(value, cfg):
    """Quantize a value tree (numeric / List / Array / Tuple) to ``cfg.precision``.

    Pure: returns a new value; the input and every object it aliases are
    never mutated. Without a precision pragma the value passes through
    untouched.
    """
    if cfg.precision is None:
        return value
    return commit_value(value, cfg)


def commit_value(value, cfg):
    """Quantize a value that comes to rest under a precision pragma.

    A value comes to rest when it is stored (variable/field/element/
    parameter binding), returned, compared, tested for truth, or when
    a statement yields it. Intermediate arithmetic is untouched, so a
    whole expression chain completes at full precision and only its
    final result is quantized: with precision 2, `1.0/3.0*3.0` rests
    as 1.0 and shows "1.00".

    The stored value and the displayed value then always agree at the
    wanted decimals. Returns a NEW value; the input is never mutated
    (a stored source object must not change as a side effect). Container
    commits rebuild fresh containers whose elements are themselves
    freshly committed; non-numeric leaves (structs, functions, errors)
    pass through by reference so identity is preserved. Without a
    precision pragma the value passes through untouched.
    """
    if cfg.precision is None:
        return value

    from B_Sharp.ASTNodes.instances import NumericValue, List, Array, Tuple

    if isinstance(value, NumericValue):
        out = _quantize_numeric(value, cfg)
    elif isinstance(value, Tuple):
        # Fresh container AND fresh elements: Tuple.copy() is a real copy,
        # but building directly also re-commits every element so no numeric
        # object is ever shared with (and mutated through) the source.
        out = Tuple([commit_value(element, cfg) for element in value.elements])
    elif isinstance(value, (List, Array)):
        # copy() gives a fresh container with the right metadata
        # (element_type, depth, is_const); replacing every element with a
        # freshly committed one removes the scalar-sharing alias.
        out = value.copy()
        out.list_of_elements = [
            commit_value(element, cfg) for element in out.list_of_elements
        ]
    else:
        return value
    try:
        out.set_context(value.context)
    except Exception:
        pass
    try:
        out.set_pos(value.pos_start, value.pos_end)
    except Exception:
        pass
    return out


def render_element(value, cfg):
    """Render one element the way it appears nested inside a list/array."""
    from B_Sharp.ASTNodes.instances import NumericValue, List, Array, Tuple

    if isinstance(value, Tuple):
        inner = ", ".join(render_element(e, cfg) for e in value.elements)
        return f"({inner})"
    if isinstance(value, (List, Array)):
        inner = ", ".join(render_element(e, cfg) for e in value.list_of_elements)
        return f"[{inner}]"
    if isinstance(value, NumericValue):
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
        Char,
        NumericValue,
        Tuple,
        ErrorInstance,
    )

    if isinstance(value, String):
        return value.value
    if isinstance(value, Char):
        return value.value
    if isinstance(value, ErrorInstance):
        try:
            if hasattr(value.error, "as_string"):
                return value.error.as_string()
            return str(value)
        except Exception:
            return str(value)
    if isinstance(value, NumericValue):
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
