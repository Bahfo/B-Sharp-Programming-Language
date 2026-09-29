import sys
import time

from B_Sharp.Errors.errors import RunTimeError
from B_Sharp.ASTNodes.instances import *


class BuiltinFunction:
    def __init__(self, name, func):
        self.name = name
        self.func = func
        self.pos_start = None
        self.pos_end = None

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def true_(self):
        return True

    def execute(self, args, interpreter, call_pos_start=None, call_pos_end=None):
        from types import SimpleNamespace
        from B_Sharp.ASTNodes.interpreter import RunTimeResult

        res = RunTimeResult()
        self.pos_start = call_pos_start
        self.pos_end = call_pos_end
        try:
            call_node = SimpleNamespace(pos_start=call_pos_start, pos_end=call_pos_end)
            result = self.func(args, context=self.context, call_node=call_node)
        except Exception as e:
            return res.failure(
                RunTimeError(
                    call_pos_start,
                    call_pos_end,
                    "RUN130",
                    {"function_name": self.name, "error_details": str(e)},
                )
            )
        if isinstance(result, tuple):
            value, error = result
            if error:
                # Errors raised inside builtins usually carry no source
                # position; stamp them with the call site so reports point
                # at the offending line.
                if error.pos_start is None or error.pos_end is None:
                    error.pos_start = call_pos_start
                    error.pos_end = call_pos_end
                return res.failure(error)
            return res.success(value)
        return res.success(result)

    def __repr__(self):
        return f"<builtin function {self.name}>"


def _render_for_print(value, call_node):
    """Python-style rendering: top-level strings unquoted, everything
    else via its repr (so nested strings inside lists stay quoted).
    Numbers honour the calling file's precision pragma."""
    from B_Sharp.CodeExecution.caller_macros import render_value, get_config

    cfg = get_config(call_node.pos_start.file_name if call_node else None)
    return render_value(value, cfg)


def _write(args, context, call_node):
    sys.stdout.write("".join(_render_for_print(arg, call_node) for arg in args))
    sys.stdout.flush()
    return Empty()


def _writeln(args, context, call_node):
    print("".join(_render_for_print(arg, call_node) for arg in args))
    return Empty()


def _format(args, context, call_node):
    import re

    from B_Sharp.CodeExecution.caller_macros import render_value, get_config
    from B_Sharp.ASTNodes.instances import Number

    if len(args) < 1:
        return None, RunTimeError(None, None, "RUN131")
    template = args[0]
    if not isinstance(template, String):
        return None, RunTimeError(None, None, "RUN132")
    cfg = get_config(call_node.pos_start.file_name if call_node else None)

    def _fmt_arg(arg):
        # Preserve historical format() rendering (repr, quoted strings) and
        # only special-case numbers when a precision pragma is active.
        if cfg.precision is not None and isinstance(arg, Number):
            return render_value(arg, cfg)
        return str(arg)

    fmt_map = {str(i): _fmt_arg(arg) for i, arg in enumerate(args[1:])}
    result = re.sub(
        r"\{(\d+)\}", lambda m: fmt_map.get(m.group(1), m.group(0)), template.value
    )
    return String(result), None


def _read(args, context, call_node):
    try:
        return String(input()), None
    except EOFError:
        return String(""), None
    except OSError as e:
        return None, RunTimeError(None, None, "RUN133", {"error_details": str(e)})
    except KeyboardInterrupt:
        return String(""), None


def _readln(args, context, call_node):
    prompt = ""
    if len(args) >= 1:
        if isinstance(args[0], String):
            prompt = args[0].value
        else:
            prompt = str(args[0])
    try:
        return String(input(prompt)), None
    except EOFError:
        return String(""), None
    except OSError as e:
        return None, RunTimeError(None, None, "RUN134", {"error_details": str(e)})
    except KeyboardInterrupt:
        return String(""), None


def _is_string(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "RUN135", {"function_name": "is_String"})
    return Boolean(isinstance(args[0], String)), None


def _is_number(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "RUN135", {"function_name": "is_Number"})
    return Boolean(isinstance(args[0], Number)), None


def _is_empty(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "RUN135", {"function_name": "is_Empty"})
    return Boolean(isinstance(args[0], Empty)), None


def _is_bool(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "RUN135", {"function_name": "is_Bool"})
    return Boolean(isinstance(args[0], Boolean)), None


def _to_number(args, context, call_node):
    from B_Sharp.CodeExecution.caller_macros import round_number, get_config

    if len(args) != 1:
        return None, RunTimeError(None, None, "RUN135", {"function_name": "to_Number"})
    val = args[0]
    cfg = get_config(call_node.pos_start.file_name if call_node else None)
    if isinstance(val, Number):
        return val, None
    if isinstance(val, String):
        s = val.value.strip()
        try:
            # Handle scientific notation and floats vs ints
            low = s.lower()
            if "." in s or "e" in low:
                num = float(s)
                # keep as float (consistent with lexer sci notation)
                return Number(round_number(num, cfg)), None
            else:
                return Number(round_number(int(s), cfg)), None
        except ValueError:
            return None, RunTimeError(None, None, "RUN136", {"value": val.value})
    if isinstance(val, Boolean):
        return Number(1 if val.value else 0), None
    return None, RunTimeError(None, None, "RUN137", {"type_name": type_spelling(val)})


def _to_string(args, context, call_node):
    from B_Sharp.CodeExecution.caller_macros import render_value, get_config

    if len(args) != 1:
        return None, RunTimeError(None, None, "RUN135", {"function_name": "to_String"})
    val = args[0]
    cfg = get_config(call_node.pos_start.file_name if call_node else None)
    if isinstance(val, String):
        return val, None
    if isinstance(val, ErrorInstance):
        try:
            return (
                String(
                    val.error.as_string()
                    if hasattr(val.error, "as_string")
                    else str(val)
                ),
                None,
            )
        except Exception:
            return String(str(val)), None
    return String(render_value(val, cfg)), None


def _time_(args, context, call_node):
    from B_Sharp.CodeExecution.caller_macros import round_number, get_config

    if len(args) != 0:
        return None, RunTimeError(None, None, "RUN138")
    cfg = get_config(call_node.pos_start.file_name if call_node else None)
    return Number(round_number(time.time(), cfg))


BUILTIN_FUNCTIONS = {
    "__write": _write,
    "__writeln": _writeln,
    "__format": _format,
    "__read": _read,
    "__readln": _readln,
    "__is_String": _is_string,
    "__is_Number": _is_number,
    "__is_Empty": _is_empty,
    "__is_Bool": _is_bool,
    "__to_Number": _to_number,
    "__to_String": _to_string,
    "__time__": _time_,
}


def register_builtins(context):
    for name, func in BUILTIN_FUNCTIONS.items():
        builtin = BuiltinFunction(name, func)
        builtin.set_context(context)
        context.variables.define(
            name=name, data_type=None, value=builtin, is_const=True
        )
