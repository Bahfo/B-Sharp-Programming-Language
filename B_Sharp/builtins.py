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
        from B_Sharp.ASTNodes.parser import RunTimeResult

        res = RunTimeResult()
        self.pos_start = call_pos_start
        self.pos_end = call_pos_end
        try:
            result = self.func(args, context=self.context, call_node=None)
        except Exception as e:
            return res.failure(
                RunTimeError(call_pos_start, call_pos_end, f"{self.name}: {e}")
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


def _render_for_print(value):
    """Python-style rendering: top-level strings unquoted, everything
    else via its repr (so nested strings inside lists stay quoted)."""
    if isinstance(value, String):
        return value.value
    return str(value)


def _write(args, context, call_node):
    sys.stdout.write("".join(_render_for_print(arg) for arg in args))
    sys.stdout.flush()
    return Empty()


def _writeln(args, context, call_node):
    print("".join(_render_for_print(arg) for arg in args))
    return Empty()


def _format(args, context, call_node):
    import re

    if len(args) < 1:
        return None, RunTimeError(
            None, None, "'format' expects at least 1 argument (template string)."
        )
    template = args[0]
    if not isinstance(template, String):
        return None, RunTimeError(
            None, None, "First argument to 'format' must be a String."
        )
    fmt_map = {str(i): str(arg) for i, arg in enumerate(args[1:])}
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
        return None, RunTimeError(None, None, f"read failed: {e}")
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
        return None, RunTimeError(None, None, f"readln failed: {e}")
    except KeyboardInterrupt:
        return String(""), None


def _is_string(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "'is_String' expects 1 argument.")
    return Boolean(isinstance(args[0], String)), None


def _is_number(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "'is_Number' expects 1 argument.")
    return Boolean(isinstance(args[0], Number)), None


def _is_empty(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "'is_Empty' expects 1 argument.")
    return Boolean(isinstance(args[0], Empty)), None


def _is_bool(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "'is_Bool' expects 1 argument.")
    return Boolean(isinstance(args[0], Boolean)), None


def _to_number(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "'to_Number' expects 1 argument.")
    val = args[0]
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
                return Number(num), None
            else:
                return Number(int(s)), None
        except ValueError:
            return None, RunTimeError(
                None, None, f"Cannot convert '{val.value}' to a number."
            )
    if isinstance(val, Boolean):
        return Number(1 if val.value else 0), None
    return None, RunTimeError(
        None, None, f"Cannot convert {type(val).__name__} to Number."
    )


def _to_string(args, context, call_node):
    if len(args) != 1:
        return None, RunTimeError(None, None, "'to_String' expects 1 argument.")
    val = args[0]
    if isinstance(val, String):
        return val, None
    return String(str(val)), None


def _time_(args, context, call_node):
    if len(args) != 0:
        return None, RunTimeError(None, None, "'time' function requires no arguments.")
    return Number(time.time())


BUILTIN_FUNCTIONS = {
    "write": _write,
    "writeln": _writeln,
    "format": _format,
    "read": _read,
    "readln": _readln,
    "is_String": _is_string,
    "is_Number": _is_number,
    "is_Empty": _is_empty,
    "is_Bool": _is_bool,
    "to_Number": _to_number,
    "to_String": _to_string,
    "time": _time_,
}


def register_builtins(context):
    for name, func in BUILTIN_FUNCTIONS.items():
        builtin = BuiltinFunction(name, func)
        builtin.set_context(context)
        context.variables.define(
            name=name, data_type=None, value=builtin, is_const=True
        )
