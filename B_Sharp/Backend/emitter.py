"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Phase-1 D emitter: literals, numeric/string operators, vars, __writeln
parity for `!pragma enforce` (fully annotated) programs. Every supported
construct carries its B# static type through emission; anything else raises
DBackendError (honest failure, never a silent mistranslation).
"""

from B_Sharp import typesys
from B_Sharp.tokens import (
    TOKEN_PLUS,
    TOKEN_MINUS,
    TOKEN_MUL,
    TOKEN_DIV,
    TOKEN_IDIV,
    TOKEN_MODULO,
    TOKEN_POWER,
    TOKEN_EE,
    TOKEN_NOT_E,
    TOKEN_LT,
    TOKEN_GT,
    TOKEN_LTE,
    TOKEN_GTE,
    TOKEN_INC,
    TOKEN_DEC,
    TOKEN_KEYWORD,
    TOKEN_IDENTIFIER,
)


class DBackendError(Exception):
    pass


def escape_d_string(s: str) -> str:
    out = s.replace("\\", "\\\\")
    out = out.replace('"', '\\"')
    out = out.replace("\n", "\\n")
    out = out.replace("\t", "\\t")
    out = out.replace("\r", "\\r")
    return f'"{out}"'


# B# type name -> D type name (Phase-1 static subset).
B2D = {
    "Short": "byte",
    "Single": "short",
    "Integer": "int",
    "Long": "long",
    "Float": "float",
    "Double": "double",
    "Bool": "bool",
    "String": "string",
    "Char": "dchar",
}

INT_KINDS = ("Short", "Single", "Integer", "Long")
FLOAT_KINDS = ("Float", "Double")
NUMERIC_KINDS = INT_KINDS + FLOAT_KINDS
INT_BITS = {"Short": 8, "Single": 16, "Integer": 32, "Long": 64}


def _d_int_literal(btype, value):
    """Load-time wrapping literal: mirrors instances wrap on construction."""
    w = typesys.wrap_signed(int(value), INT_BITS[btype])
    t = B2D[btype]
    if btype == "Long" and w == -(1 << 63):
        return "(cast(long)0x8000000000000000)"
    return f"(cast({t})({w}))"


def _d_float_literal(btype, value):
    if btype == "Float":
        v = typesys.to_f32(float(value))
        text = typesys.f32_repr(v)
        if "." not in text and "e" not in text and "n" not in text:
            text += ".0"
        return text + "f"
    text = str(float(value))
    if "." not in text and "e" not in text and "n" not in text:
        text += ".0"
    return text


def _promote_int(a, b):
    return a if INT_BITS[a] >= INT_BITS[b] else b


def _promote_numeric(a, b):
    # Mirrors typesys.promote for the Phase-1 subset (no NaN/Inf nodes).
    if a == b:
        return a
    a_int, b_int = a in INT_KINDS, b in INT_KINDS
    if a_int and b_int:
        return _promote_int(a, b)
    if a in FLOAT_KINDS and b in FLOAT_KINDS:
        return "Double"
    if a_int and b in FLOAT_KINDS:
        return "Double" if (a == "Long" or b == "Double") else "Float"
    if b_int and a in FLOAT_KINDS:
        return "Double" if (b == "Long" or a == "Double") else "Float"
    return None


class DLanguageEmitter:
    """
    Base emitter from B-Sharp to the D Programming Language.
    """

    def __init__(self):
        self.symbols = {}

    def emit(self, root) -> str:
        if type(root).__name__ != "StatementsNode":
            raise DBackendError(f"Unsupported {type(root).__name__}")
        self.symbols = {}
        body = self.visit_StatementsNode(root)
        return "import bsruntime;\nimport std.stdio;\nvoid main()\n{\n" + body + "}\n"

    # ---------------- statements ----------------

    def visit_StatementsNode(self, node) -> str:
        lines = ""
        for stmt in node.statement_nodes:
            lines += self.emit_statement(stmt)
        return lines

    def emit_statement(self, node) -> str:
        kind = type(node).__name__
        if kind == "VariableAssignNode":
            return self.emit_var_decl([node.name], node.data_type, node.value, node.is_const)
        if kind == "MultiVariableAssignNode":
            return self.emit_var_decl(node.names, node.data_type, node.value, node.is_const)
        if kind == "VariableReassignNode":
            return self.emit_reassign(node)
        if kind == "IncrementNode":
            code, _ = self.emit_increment(node)
            return "    " + code + ";\n"
        # Expression statement (e.g. a __writeln call).
        code, _ = self.emit_expr(node)
        return "    " + code + ";\n"

    def _declared_dtype(self, type_tok):
        if type_tok is None or type_tok is False:
            return None
        name = type_tok.value
        if name not in B2D:
            raise DBackendError(f"Unsupported declaration type '{name}'")
        if "[" in name or name.startswith("Tuple"):
            raise DBackendError(f"Unsupported declaration type '{name}'")
        return name

    def _convert_to_declared(self, code, inferred, declared):
        if inferred == declared:
            return code
        if inferred in INT_KINDS and declared in INT_KINDS:
            return f"cast({B2D[declared]})({code})"
        if inferred in FLOAT_KINDS and declared in FLOAT_KINDS:
            return f"cast({B2D[declared]})({code})"
        raise DBackendError(f"Cannot convert {inferred} to {declared}")

    def emit_var_decl(self, names, type_tok, value_node, is_const):
        declared = self._declared_dtype(type_tok)
        if value_node is None:
            raise DBackendError("Declaration without a value is unsupported in Phase 1")
        code, inferred = self.emit_expr(value_node)
        if declared is None:
            # Dynamic mode: infer from the initializer.
            if inferred not in B2D:
                raise DBackendError(f"Cannot infer D type for {inferred}")
            declared = inferred
            init = code
        else:
            init = self._convert_to_declared(code, inferred, declared)
        dtype = B2D[declared]
        for tok in names:
            if tok.value in self.symbols:
                raise DBackendError(f"Redefinition of '{tok.value}'")
            self.symbols[tok.value] = declared
        if len(names) == 1:
            decl = f"{dtype} {names[0].value} = {init};"
        else:
            decl = ", ".join(f"{n.value} = {init}" for n in names)
            decl = f"{dtype} {decl};"
        if is_const:
            decl = "immutable " + decl
        return "    " + decl + "\n"

    def emit_reassign(self, node):
        name = node.name.value
        if name not in self.symbols:
            raise DBackendError(f"Assignment to undeclared '{name}'")
        declared = self.symbols[name]
        code, inferred = self.emit_expr(node.value)
        init = self._convert_to_declared(code, inferred, declared)
        return f"    {name} = {init};\n"

    # ---------------- expressions: (code, B# type) ----------------

    def emit_expr(self, node):
        kind = type(node).__name__
        fn = getattr(self, f"expr_{kind}", None)
        if fn is None:
            raise DBackendError(f"Unsupported {kind}")
        return fn(node)

    # Keep the old visitor protocol working for Tools/emit_d.py-style callers.
    def visit(self, node) -> str:
        code, _ = self.emit_expr(node)
        return code

    def visit_StringNode(self, node) -> str:
        return escape_d_string(node.token.value)

    def expr_NumberNode(self, node):
        lit = getattr(node, "literal_type", "Long")
        if lit in INT_KINDS:
            return _d_int_literal(lit, node.token.value), lit
        if lit in FLOAT_KINDS:
            return _d_float_literal(lit, node.token.value), lit
        raise DBackendError(f"Unsupported numeric literal type '{lit}'")

    def expr_BooleanNode(self, node):
        return ("true" if node.token.value == "true" else "false"), "Bool"

    def expr_StringNode(self, node):
        return escape_d_string(node.token.value), "String"

    def expr_CharNode(self, node):
        v = node.token.value
        esc = {"\\": "\\\\", "'": "\\'", "\n": "\\n", "\t": "\\t", "\r": "\\r"}.get(v, v)
        return f"cast(dchar)'{esc}'", "Char"

    def expr_VariableAccessNode(self, node):
        name = node.name.value
        if name not in self.symbols:
            raise DBackendError(f"Use of undeclared variable '{name}'")
        return name, self.symbols[name]

    def expr_UnaryOpNode(self, node):
        operand, otype = self.emit_expr(node.node)
        t = node.op_token.type
        v = node.op_token.value
        if t == TOKEN_MINUS:
            if otype not in NUMERIC_KINDS:
                raise DBackendError(f"Unary minus on {otype}")
            if otype in INT_KINDS and otype != "Long":
                return f"(cast({B2D[otype]})(-{operand}))", otype
            return f"(-{operand})", otype
        if t == TOKEN_PLUS:
            if otype not in NUMERIC_KINDS:
                raise DBackendError(f"Unary plus on {otype}")
            return f"({operand})", otype
        if t == TOKEN_KEYWORD and v == "not":
            if otype != "Bool":
                raise DBackendError(f"'not' on {otype}")
            return f"(!{operand})", "Bool"
        raise DBackendError(f"Unsupported unary operator '{v or t}'")

    def _is_negative_int_literal(self, node):
        if type(node).__name__ == "UnaryOpNode" and node.op_token.type == TOKEN_MINUS:
            inner = node.node
            if type(inner).__name__ == "NumberNode" and getattr(inner, "literal_type", "") in INT_KINDS:
                return True
        return False

    def expr_BinaryOpNode(self, node):
        left, ltype = self.emit_expr(node.left_node)
        right, rtype = self.emit_expr(node.right_node)
        t = node.op_token.type
        v = node.op_token.value

        if t == TOKEN_KEYWORD and v in ("and", "or"):
            if ltype != "Bool" or rtype != "Bool":
                raise DBackendError(f"'{v}' on non-Bool ({ltype}, {rtype})")
            return (f"({left} && {right})" if v == "and" else f"({left} || {right})"), "Bool"

        if (t == TOKEN_EE) or (t == TOKEN_KEYWORD and v == "is"):
            return self._emit_equality(left, ltype, right, rtype, negated=False)
        if t == TOKEN_NOT_E:
            return self._emit_equality(left, ltype, right, rtype, negated=True)
        if t in (TOKEN_LT, TOKEN_GT, TOKEN_LTE, TOKEN_GTE):
            return self._emit_ordering(left, ltype, right, rtype, t)

        if t in (TOKEN_PLUS, TOKEN_MINUS, TOKEN_MUL):
            return self._emit_additive(left, ltype, right, rtype, t)
        if t == TOKEN_DIV:
            return self._emit_div(left, ltype, right, rtype)
        if t == TOKEN_IDIV:
            return self._emit_idiv(left, ltype, right, rtype)
        if t == TOKEN_MODULO:
            return self._emit_mod(left, ltype, right, rtype)
        if t == TOKEN_POWER:
            return self._emit_power(node, left, ltype, right, rtype)
        raise DBackendError(f"Unsupported binary operator '{v or t}'")

    def _emit_equality(self, left, ltype, right, rtype, negated):
        op = "!=" if negated else "=="
        if ltype in NUMERIC_KINDS and rtype in NUMERIC_KINDS:
            return f"({left} {op} {right})", "Bool"
        if ltype == "Bool" and rtype == "Bool":
            return f"({left} {op} {right})", "Bool"
        if (ltype in NUMERIC_KINDS and rtype == "Bool") or (ltype == "Bool" and rtype in NUMERIC_KINDS):
            num, b = (left, right) if rtype == "Bool" else (right, left)
            return self._eq_bool_num(num, b, negated)
        if ltype == "String" and rtype == "String":
            return f"({left} {op} {right})", "Bool"
        if ltype == "Char" and rtype == "Char":
            return f"({left} {op} {right})", "Bool"
        # B# cross-type equality is false (not an error): mirror it.
        return ("true" if negated else "false"), "Bool"

    def _eq_bool_num(self, num, b, negated):
        # B# coerces Bool to 1/0 for numeric equality.
        comp = f"({num} == ({b} ? 1 : 0))"
        if negated:
            comp = f"({num} != ({b} ? 1 : 0))"
        return comp, "Bool"

    def _emit_ordering(self, left, ltype, right, rtype, t):
        op = {TOKEN_LT: "<", TOKEN_GT: ">", TOKEN_LTE: "<=", TOKEN_GTE: ">="}[t]
        if ltype in NUMERIC_KINDS and rtype in NUMERIC_KINDS:
            return f"({left} {op} {right})", "Bool"
        if ltype == "String" and rtype == "String":
            return f"({left} {op} {right})", "Bool"
        if ltype == "Char" and rtype == "Char":
            return f"({left} {op} {right})", "Bool"
        raise DBackendError(f"Ordering comparison on ({ltype}, {rtype})")

    def _emit_additive(self, left, ltype, right, rtype, t):
        op = {TOKEN_PLUS: "+", TOKEN_MINUS: "-", TOKEN_MUL: "*"}[t]
        if ltype in NUMERIC_KINDS and rtype in NUMERIC_KINDS:
            target = _promote_numeric(ltype, rtype)
            if target is None:
                raise DBackendError(f"Arithmetic on ({ltype}, {rtype})")
            if target in INT_KINDS and target != "Long":
                return f"(cast({B2D[target]})({left} {op} {right}))", target
            return f"({left} {op} {right})", target
        if t == TOKEN_PLUS and (ltype in ("String", "Char") or rtype in ("String", "Char")):
            return self._emit_concat(left, ltype, right, rtype)
        if t == TOKEN_MUL:
            rep = self._emit_repeat(left, ltype, right, rtype)
            if rep is not None:
                return rep
        raise DBackendError(f"Arithmetic '{op}' on ({ltype}, {rtype})")

    def _as_string(self, code, btype):
        if btype == "String":
            return code
        if btype == "Char":
            return f"bsToStr({code})"
        if btype in NUMERIC_KINDS or btype == "Bool":
            return f"bsToStr({code})"
        raise DBackendError(f"Cannot concatenate {btype}")

    def _emit_concat(self, left, ltype, right, rtype):
        if ltype not in ("String", "Char", *NUMERIC_KINDS, "Bool"):
            raise DBackendError(f"Concatenation on ({ltype}, {rtype})")
        if rtype not in ("String", "Char", *NUMERIC_KINDS, "Bool"):
            raise DBackendError(f"Concatenation on ({ltype}, {rtype})")
        if ltype == "Char" and rtype == "Char":
            return f"(\"\" ~ bsToStr({left}) ~ bsToStr({right}))", "String"
        return f"({self._as_string(left, ltype)} ~ {self._as_string(right, rtype)})", "String"

    def _emit_repeat(self, left, ltype, right, rtype):
        if ltype == "String" and rtype in INT_KINDS:
            return f"bsRepeat({left}, cast(long)({right}))", "String"
        if rtype == "String" and ltype in INT_KINDS:
            return f"bsRepeat({right}, cast(long)({left}))", "String"
        return None

    def _emit_div(self, left, ltype, right, rtype):
        if ltype not in NUMERIC_KINDS or rtype not in NUMERIC_KINDS:
            raise DBackendError(f"Division on ({ltype}, {rtype})")
        return f"bsDiv({left}, {right})", "Double"

    def _emit_idiv(self, left, ltype, right, rtype):
        if ltype not in INT_KINDS or rtype not in INT_KINDS:
            raise DBackendError(f"Integer division on ({ltype}, {rtype})")
        target = _promote_int(ltype, rtype)
        return f"bsIdiv!({B2D[target]})({left}, {right})", target

    def _emit_mod(self, left, ltype, right, rtype):
        if ltype not in INT_KINDS or rtype not in INT_KINDS:
            raise DBackendError(f"Remainder on ({ltype}, {rtype})")
        target = _promote_int(ltype, rtype)
        return f"bsMod!({B2D[target]})({left}, {right})", target

    def _emit_power(self, node, left, ltype, right, rtype):
        if ltype not in NUMERIC_KINDS or rtype not in NUMERIC_KINDS:
            raise DBackendError(f"Power on ({ltype}, {rtype})")
        target = _promote_numeric(ltype, rtype)
        if target in INT_KINDS:
            if self._is_negative_int_literal(node.right_node):
                return f"bsPowD({left}, {right})", "Double"
            return f"bsPowI!({B2D[target]})({left}, {right})", target
        return f"bsPowD({left}, {right})", target

    def expr_CastNode(self, node):
        code, stype = self.emit_expr(node.value_node)
        target = node.type_tok.value
        if stype not in NUMERIC_KINDS:
            raise DBackendError(f"cast from {stype} is Phase 5")
        fn = {
            "Long": "bsCastLong",
            "Integer": "bsCastInteger",
            "Single": "bsCastSingle",
            "Short": "bsCastShort",
            "Double": "bsCastDouble",
            "Float": "bsCastFloat",
        }.get(target)
        if fn is None:
            raise DBackendError(f"cast to '{target}' is unsupported in Phase 1")
        return f"{fn}({code})", target

    def expr_PropertyAccessNode(self, node):
        obj, otype = self.emit_expr(node.node)
        prop = node.property_name_token.value
        if prop == "type":
            if otype not in B2D:
                raise DBackendError(f".type on {otype}")
            return f'"{otype}"', "String"
        raise DBackendError(f"Unsupported property '.{prop}'")

    def emit_increment(self, node):
        from B_Sharp.tokens import TOKEN_INC as _INC

        name = node.var_name_tok.value
        if name not in self.symbols:
            raise DBackendError(f"Increment of undeclared '{name}'")
        if self.symbols[name] not in INT_KINDS:
            raise DBackendError(f"Increment of {self.symbols[name]}")
        op = "++" if node.op_tok.type == _INC else "--"
        if node.is_postfix:
            return f"{name}{op}", self.symbols[name]
        return f"{op}{name}", self.symbols[name]

    def expr_IncrementNode(self, node):
        return self.emit_increment(node)

    def expr_CallNode(self, node):
        inner = node.node_to_call
        if type(inner).__name__ != "VariableAccessNode":
            raise DBackendError("Unsupported call target")
        callee = inner.name.value
        if callee == "__writeln":
            parts = []
            for arg in node.arg_nodes:
                code, atype = self.emit_expr(arg)
                if atype not in (*NUMERIC_KINDS, "Bool", "String", "Char"):
                    raise DBackendError(f"__writeln of {atype}")
                parts.append(f"bsToStr({code})" if atype != "String" else code)
            if not parts:
                return "writeln()", "Empty"
            return "writeln(" + " ~ ".join(parts) + ")", "Empty"
        if callee == "__to_String":
            if len(node.arg_nodes) != 1:
                raise DBackendError("__to_String requires one argument")
            code, atype = self.emit_expr(node.arg_nodes[0])
            if atype not in (*NUMERIC_KINDS, "Bool", "String", "Char"):
                raise DBackendError(f"__to_String of {atype}")
            if atype == "String":
                return f"({code})", "String"
            return f"bsToStr({code})", "String"
        if callee == "__format":
            if not node.arg_nodes:
                raise DBackendError("__format requires a template")
            tcode, ttype = self.emit_expr(node.arg_nodes[0])
            if ttype != "String":
                raise DBackendError("__format template must be a String")
            reps = []
            for arg in node.arg_nodes[1:]:
                code, atype = self.emit_expr(arg)
                if atype not in (*NUMERIC_KINDS, "Bool", "String", "Char"):
                    raise DBackendError(f"__format of {atype}")
                reps.append(f"bsRepr({code})")
            return f"bsFormat({tcode}, [{', '.join(reps)}])", "String"
        raise DBackendError(f"Unsupported call '{callee}'")
