# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
# The source code of B_Sharp Programming Language.
# The code is guarded and licensed under the GPLv3 License.
# ----------------------------------------------------------------
# Module: parser.py: House of Parser of B-Sharp.

import os
import sys

from B_Sharp.tokens import *
from B_Sharp.Errors.errors import *
from B_Sharp.ASTNodes.instances import *
from B_Sharp.ASTNodes.nodes import *
from B_Sharp.builtins import BuiltinFunction, register_builtins

MAX_PARSE_DEPTH = 350
_RECERSION_HEADROOM_LIMIT = 8000

_VALID_TYPES_MESSAGE = (
    "Valid types (uppercase required): "
    "Bool, Number, String, Empty, List, Inf, NaN, Function, "
    "Number[], String[], Boolean[], Empty[]."
)


class ParseDepthExceeded(Exception):
    """Internal signal: source nesting exceeded MAX_PARSE_DEPTH."""


def _with_recursion_headroom(fn):
    """Runs fn with a temporarily raised Python recursion limit.

    The limit is only raised on the outermost call and restored afterwards,
    so the process-global setting is never permanently mutated.
    """

    def wrapper(*args, **kwargs):
        limit = sys.getrecursionlimit()
        if limit >= _RECERSION_HEADROOM_LIMIT:
            return fn(*args, **kwargs)
        sys.setrecursionlimit(_RECERSION_HEADROOM_LIMIT)
        try:
            return fn(*args, **kwargs)
        finally:
            sys.setrecursionlimit(limit)

    return wrapper


class ParserResults:
    def __init__(self):
        self.error = None
        self.node = None
        self.forward_count = 0

    def register(self, res):
        if isinstance(res, ParserResults):
            if res.error:
                self.error = res.error
            return res.node
        return res

    def register_forward(self):
        self.forward_count += 1

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        if not self.error or self.forward_count == 0:
            self.error = error

        return self


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.token_index = -1
        self.current_token = None
        self.depth = 0
        self.forward()

    def forward(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        return self.current_token

    def _depth_enter(self):
        self.depth += 1
        if self.depth > MAX_PARSE_DEPTH:
            raise ParseDepthExceeded()

    def _depth_exit(self):
        self.depth -= 1

    def _skip_newlines(self, res):
        while self.current_token.type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
            res.register_forward()
            self.forward()

    ################################################################
    # Grammar Rules
    # Precedence (lowest to highest):
    #   expression  → and | or
    #   comparison  → == != < > <= >=
    #   term        → + -
    #   factor      → * /
    #   unary       → + - not
    #   power       → ^
    #   atom        → INT FLOAT BOOLEAN IDENTIFIER none (expr)
    ################################################################

    def atom(self):
        self._depth_enter()
        try:
            return self._atom()
        finally:
            self._depth_exit()

    def _atom(self):
        res = ParserResults()
        tok = self.current_token

        # Prefix ++x or --x
        if tok.type in (TOKEN_INC, TOKEN_DEC):
            return self.increment_or_decrement()

        # Identifier: Var access OR Postfix x++ / x--
        elif tok.type == TOKEN_IDENTIFIER:
            var_tok = tok
            res.register_forward()
            self.forward()

            if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
                op_tok = self.current_token
                res.register_forward()
                self.forward()
                return res.success(IncrementNode(var_tok, op_tok, is_postfix=True))

            return res.success(VariableAccessNode(var_tok))

        elif tok.type in (TOKEN_INT, TOKEN_FLOAT):
            res.register_forward()
            self.forward()
            return res.success(NumberNode(tok))

        elif tok.type == TOKEN_STRING:
            res.register_forward()
            self.forward()
            return res.success(StringNode(tok))

        elif tok.type == TOKEN_LPAREN:
            res.register_forward()
            self.forward()
            self._skip_newlines(res)
            expr = res.register(self.expression())
            if res.error:
                return res
            self._skip_newlines(res)
            if self.current_token.type == TOKEN_RPAREN:
                res.register_forward()
                self.forward()
                return res.success(expr)
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN006",
                )
            )

        elif self.current_token.type == TOKEN_LBRACKET:
            list_expression = res.register(self.make_list())
            if res.error:
                return res

            return res.success(list_expression)

        elif tok.type == TOKEN_KEYWORD and tok.value in ("true", "false"):
            res.register_forward()
            self.forward()
            return res.success(BooleanNode(tok))

        elif tok.type == TOKEN_KEYWORD and tok.value == "none":
            res.register_forward()
            self.forward()
            return res.success(NoneNode(tok))

        elif tok.type == TOKEN_KEYWORD and tok.value == "if":
            return self.if_expression()

        elif tok.type == TOKEN_KEYWORD and tok.value == "nan":
            return self._not_a_number()

        elif tok.type == TOKEN_KEYWORD and tok.value == "inf":
            return self._infinity_value()

        return res.failure(
            B_SharpSyntaxError(
                tok.pos_start,
                tok.pos_end,
                "SYN007",
            )
        )

    def _not_a_number(self):
        res = ParserResults()

        pos_start = self.current_token.pos_start.copy()

        res.register_forward()
        self.forward()

        return res.success(NaNNode(pos_start))

    def _infinity_value(self):
        res = ParserResults()

        pos_start = self.current_token.pos_start.copy()

        res.register_forward()
        self.forward()

        return res.success(InfinityNode(pos_start))

    def import_module(self):
        res = ParserResults()
        pos_start = self.current_token.pos_start.copy()

        if self.current_token.type != TOKEN_KEYWORD:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN008",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_STRING:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN009",
                )
            )

        file_path_node = res.register(self.atom())
        if res.error:
            return res

        raw_import_str = file_path_node.token.value
        pos_end = file_path_node.pos_end

        if ":" in raw_import_str:
            file_path_str, symbols_str = raw_import_str.split(":", 1)
            symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
        else:
            file_path_str = raw_import_str
            symbols = None

        resolved = self.resolve_import_path(file_path_str)
        if resolved is None:
            return res.failure(
                RunTimeError(
                    pos_start,
                    pos_end,
                    "RUN026",
                    {"file_path": file_path_str},
                )
            )

        return res.success(ImportNode(resolved, symbols, pos_start, pos_end))

    def resolve_import_path(self, file_path: str):
        try:
            if os.path.isabs(file_path):
                resolved = os.path.abspath(file_path)
            else:
                caller_dir = (
                    os.path.dirname(os.path.abspath(self.tokens[0].pos_start.file_name))
                    if self.tokens and self.tokens[0].pos_start
                    else os.getcwd()
                )
                resolved = os.path.abspath(os.path.join(caller_dir, file_path))

            if not os.path.exists(resolved):
                if not resolved.endswith(".bsharp"):
                    resolved_with_ext = resolved + ".bsharp"
                    if os.path.exists(resolved_with_ext):
                        return resolved_with_ext
                return None

            return resolved
        except Exception:
            return None

    def if_expression(self):
        res = ParserResults()
        cases = []
        else_case = None

        if not self.current_token.matches(TOKEN_KEYWORD, "if"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN010",
                )
            )

        res.register_forward()
        self.forward()

        condition = res.register(self.expression())
        if res.error:
            return res

        # Check for block '{' or keyword 'then'
        if self.current_token.type == TOKEN_LCURLY:
            expr = res.register(self.block())
            if res.error:
                return res
            cases.append((condition, expr))
        elif self.current_token.matches(TOKEN_KEYWORD, "then"):
            res.register_forward()
            self.forward()
            expr = res.register(self.statement())
            if res.error:
                return res
            cases.append((condition, expr))
        else:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN011",
                )
            )

        # Handle 'elif' clauses
        while self.current_token.matches(TOKEN_KEYWORD, "elif"):
            res.register_forward()
            self.forward()

            condition = res.register(self.expression())
            if res.error:
                return res

            if self.current_token.type == TOKEN_LCURLY:
                expr = res.register(self.block())
                if res.error:
                    return res
                cases.append((condition, expr))
            elif self.current_token.matches(TOKEN_KEYWORD, "then"):
                res.register_forward()
                self.forward()
                expr = res.register(self.statement())
                if res.error:
                    return res
                cases.append((condition, expr))
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN012",
                    )
                )

        # Handle 'else' clause
        if self.current_token.matches(TOKEN_KEYWORD, "else"):
            res.register_forward()
            self.forward()

            if self.current_token.type == TOKEN_LCURLY:
                else_case = res.register(self.block())
                if res.error:
                    return res
            elif self.current_token.matches(TOKEN_KEYWORD, "then"):
                res.register_forward()
                self.forward()
                else_case = res.register(self.statement())
                if res.error:
                    return res
            else:
                else_case = res.register(self.statement())
                if res.error:
                    return res

        return res.success(IfNode(cases, else_case))

    def power(self):
        res = ParserResults()
        left = res.register(self.call())
        if res.error:
            return res

        if self.current_token.type == TOKEN_POWER:
            op_token = self.current_token
            res.register(self.forward())
            right = res.register(self.unary())
            if res.error:
                return res
            left = BinaryOpNode(left, op_token, right)

        return res.success(left)

    def unary(self):
        self._depth_enter()
        try:
            return self._unary()
        finally:
            self._depth_exit()

    def _unary(self):
        res = ParserResults()
        token = self.current_token

        if token.type in (TOKEN_PLUS, TOKEN_MINUS):
            res.register(self.forward())
            operand = res.register(self.unary())
            if res.error:
                return res
            return res.success(UnaryOpNode(token, operand))

        if token.type == TOKEN_KEYWORD and token.value == "not":
            res.register(self.forward())
            operand = res.register(self.unary())
            if res.error:
                return res
            return res.success(UnaryOpNode(token, operand))

        return self.power()

    COMPARISON_TOKENS = (
        TOKEN_EE,
        TOKEN_NOT_E,
        TOKEN_LT,
        TOKEN_GT,
        TOKEN_LTE,
        TOKEN_GTE,
    )

    def factor(self):
        return self.binary_operation(
            self.unary, (TOKEN_MUL, TOKEN_DIV, TOKEN_IDIV, TOKEN_MODULO)
        )

    def term(self):
        return self.binary_operation(self.factor, (TOKEN_PLUS, TOKEN_MINUS))

    def comparison(self):
        res = ParserResults()
        left = res.register(self.term())
        if res.error:
            return res

        if self.current_token.type in self.COMPARISON_TOKENS:
            op_token = self.current_token
            res.register(self.forward())
            right = res.register(self.term())
            if res.error:
                return res
            left = BinaryOpNode(left, op_token, right)

            if self.current_token.type in self.COMPARISON_TOKENS:
                return res.failure(
                    ComparisonError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "CMP001",
                    )
                )

        return res.success(left)

    def and_expression(self):
        return self.binary_operation(self.comparison, ("and",))

    def or_expression(self):
        return self.binary_operation(self.and_expression, ("or",))

    def expression(self):
        return self.or_expression()

    def binary_operation(self, function, operations):
        res = ParserResults()
        left = res.register(function())
        if res.error:
            return res

        while self.current_token.type in operations or (
            self.current_token.type == TOKEN_KEYWORD
            and self.current_token.value in operations
        ):
            op_token = self.current_token
            res.register(self.forward())
            right = res.register(function())

            if res.error:
                return res

            left = BinaryOpNode(left, op_token, right)

        return res.success(left)

    ################################################################
    # Variable Parsing Rules
    ################################################################

    def _parse_array_suffix(self, type_tok):
        """Check for [] suffix after a type token. Returns (modified_token, error)."""
        if self.current_token.type == TOKEN_LBRACKET:
            self.forward()
            if self.current_token.type != TOKEN_RBRACKET:
                return None, B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN013",
                )
            self.forward()
            if type_tok.value == "List":
                return None, B_SharpSyntaxError(
                    type_tok.pos_start,
                    type_tok.pos_end,
                    "SYN014",
                )
            type_tok.value = type_tok.value + "[]"
        return type_tok, None

    def var_decl(self):
        """Parses variable declarations:
        `var x : Number = 10`
        `const y = 12`
        `var x, y, z : Number = 15`
        """
        res = ParserResults()
        is_const = self.current_token.value == "const"
        start_tok = self.current_token
        res.register(self.forward())

        if self.current_token.type != TOKEN_IDENTIFIER:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN015",
                )
            )

        names = [self.current_token]
        res.register(self.forward())

        while self.current_token.type == TOKEN_COMMA:
            res.register(self.forward())
            if self.current_token.type != TOKEN_IDENTIFIER:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN016",
                    )
                )
            names.append(self.current_token)
            res.register(self.forward())

        type_tok = None
        if self.current_token.type == TOKEN_COLON:
            res.register(self.forward())
            if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                type_tok = self.current_token
                res.register(self.forward())
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN017",
                    )
                )

            type_tok, err = self._parse_array_suffix(type_tok)
            if err:
                return res.failure(err)

            if TYPE_MAP.get(type_tok.value) is None:
                    return res.failure(
                        B_SharpSyntaxError(
                            type_tok.pos_start,
                            type_tok.pos_end,
                            "SYN018",
                            {"type_name": type_tok.value},
                        )
                    )

        value_node = None
        if self.current_token.type == TOKEN_EQUAL:
            res.register(self.forward())

            if (
                self.current_token.type == TOKEN_KEYWORD
                and self.current_token.value in ("var", "const")
            ):
                value_node = res.register(self.var_decl())
            else:
                value_node = res.register(self.expression())

            if res.error:
                return res

            if self.current_token.type == TOKEN_COMMA:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN019",
                    )
                )

        if is_const and type_tok is None and value_node is None:
            return res.failure(
                B_SharpSyntaxError(
                    start_tok.pos_start,
                    self.current_token.pos_end,
                    "SYN020",
                )
            )

        if len(names) == 1:
            return res.success(
                VariableAssignNode(
                    names[0], value_node, is_const=is_const, type_define=type_tok
                )
            )
        else:
            return res.success(
                MultiVariableAssignNode(
                    names, value_node, is_const=is_const, type_define=type_tok
                )
            )

    def make_list(self):
        res = ParserResults()
        list_of_elements = []
        pos_start = self.current_token.pos_start.copy()

        if self.current_token.type != TOKEN_LBRACKET:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN021",
                )
            )

        res.register_forward()
        self.forward()

        self._skip_newlines(res)

        if self.current_token.type == TOKEN_RBRACKET:
            res.register_forward()
            self.forward()
            return res.success(
                ListNode(list_of_elements, pos_start, self.current_token.pos_end.copy())
            )

        else:
            list_of_elements.append(res.register(self.expression()))
            if res.error:
                    return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN022",
                    )
                )

            while self.current_token.type == TOKEN_COMMA:
                res.register_forward()
                self.forward()
                self._skip_newlines(res)

                if self.current_token.type == TOKEN_RBRACKET:
                    break

                list_of_elements.append(res.register(self.expression()))
                if res.error:
                    return res

            self._skip_newlines(res)

            if self.current_token.type != TOKEN_RBRACKET:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN023",
                    )
                )

            res.register_forward()
            self.forward()

            return res.success(
                ListNode(list_of_elements, pos_start, self.current_token.pos_end.copy())
            )

    def try_statement(self):
        self._depth_enter()
        try:
            return self._try_statement()
        finally:
            self._depth_exit()

    def _try_statement(self):
        res = ParserResults()
        pos_start = self.current_token.pos_start.copy()

        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN024",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type == TOKEN_RCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN025",
                )
            )

        body_node = res.register(self.statements())
        if res.error:
            return res

        if not body_node.statement_nodes:
            return res.failure(
                B_SharpSyntaxError(
                    pos_start,
                    self.current_token.pos_end,
                    "SYN025",
                )
            )

        if self.current_token.type != TOKEN_RCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN026",
                )
            )

        rcurly_pos = self.current_token.pos_end.copy()
        res.register_forward()
        self.forward()

        catch_nodes = []
        while True:
            temp_idx = self.token_index
            while temp_idx < len(self.tokens) and self.tokens[temp_idx].type in (
                TOKEN_NEWLINE,
                TOKEN_SEMICOLON,
            ):
                temp_idx += 1
            if temp_idx >= len(self.tokens) or not self.tokens[temp_idx].matches(
                TOKEN_KEYWORD, "catch"
            ):
                break
            self._skip_newlines(res)
            if not self.current_token.matches(TOKEN_KEYWORD, "catch"):
                break
            catch_pos_start = self.current_token.pos_start.copy()
            res.register_forward()
            self.forward()

            if self.current_token.type != TOKEN_LPAREN:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN027",
                    )
                )
            res.register_forward()
            self.forward()

            if self.current_token.type not in (TOKEN_IDENTIFIER, TOKEN_KEYWORD):
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN028",
                    )
                )
            exception_tok = self.current_token
            if ERROR_TYPE_MAP.get(exception_tok.value) is None:
                return res.failure(
                    B_SharpSyntaxError(
                        exception_tok.pos_start,
                        exception_tok.pos_end,
                        "SYN029",
                        {"error_type": exception_tok.value},
                    )
                )
            res.register_forward()
            self.forward()

            exception_var_tok = None
            if self.current_token.type == TOKEN_IDENTIFIER:
                exception_var_tok = self.current_token
                res.register_forward()
                self.forward()

            if self.current_token.type != TOKEN_RPAREN:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN030",
                    )
                )
            res.register_forward()
            self.forward()

            self._skip_newlines(res)

            if self.current_token.type != TOKEN_LCURLY:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN031",
                    )
                )

            catch_body = res.register(self.block())
            if res.error:
                return res

            catch_pos_end = (
                catch_body.pos_end.copy()
                if catch_body.pos_end
                else catch_pos_start.copy()
            )
            catch_nodes.append(
                CatchNode(
                    catch_pos_start,
                    catch_pos_end,
                    catch_body,
                    exception=exception_tok,
                    exception_var=exception_var_tok,
                )
            )

        if not catch_nodes:
            return res.failure(
                B_SharpSyntaxError(
                    pos_start,
                    rcurly_pos,
                    "SYN032",
                )
            )

        final_pos_end = catch_nodes[-1].pos_end.copy()
        return res.success(
            TryCatchNode(pos_start, final_pos_end, body_node, catch_nodes)
        )

    def statement(self):
        res = ParserResults()

        if self.current_token.matches(TOKEN_KEYWORD, "pass"):
            tok = self.current_token
            res.register_forward()
            self.forward()
            return res.success(PassNode(tok.pos_start, tok.pos_end))

        elif self.current_token.matches(TOKEN_KEYWORD, "break"):
            tok = self.current_token
            res.register_forward()
            self.forward()
            return res.success(BreakNode(tok.pos_start, tok.pos_end))

        elif self.current_token.matches(TOKEN_KEYWORD, "continue"):
            tok = self.current_token
            res.register_forward()
            self.forward()
            return res.success(ContinueNode(tok.pos_start, tok.pos_end))

        if self.current_token.type == TOKEN_KEYWORD:
            if self.current_token.value in ("var", "const"):
                return self.var_decl()
            elif self.current_token.value in ("fn", "function"):
                return self.fn_def()
            elif self.current_token.value == "return":
                return self.return_statement()
            elif self.current_token.value == "if":
                return self.if_expression()
            elif self.current_token.value == "while":
                return self.while_expression()
            elif self.current_token.value == "do":
                return self.do_expression()
            elif self.current_token.value == "for":
                return self.for_expression()
            elif self.current_token.value == "using":
                return self.import_module()
            elif self.current_token.value == "try":
                return self.try_statement()
            elif self.current_token.value == "struct":
                return self.struct_def()

        # Prefix ++i / --i
        if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
            return self.increment_or_decrement()

        # Check for identifier actions: assignment or postfix i++ / i--
        if self.current_token.type == TOKEN_IDENTIFIER and self.token_index + 1 < len(
            self.tokens
        ):
            next_tok = self.tokens[self.token_index + 1]

            if next_tok.type == TOKEN_EQUAL:
                name_tok = self.current_token
                res.register(self.forward())
                res.register(self.forward())
                value_node = res.register(self.expression())
                if res.error:
                    return res
                return res.success(VariableReassignNode(name_tok, value_node))

        # Dynamic index assignment: e.g. a[0] = 5, a[0][1] = 5, obj.prop[0] = 5
        # Speculative parse of call chain then check for '='
        saved_index = self.token_index
        saved_token = self.current_token
        saved_depth = self.depth
        temp_res = ParserResults()
        lhs = temp_res.register(self.call())
        if not temp_res.error and self.current_token.type == TOKEN_EQUAL:
            if isinstance(lhs, IndexAccessNode):
                res.register(self.forward())  # consume '='
                value_node = res.register(self.expression())
                if res.error:
                    return res
                return res.success(IndexAssignNode(lhs, value_node))

            if isinstance(lhs, PropertyAccessNode):
                res.register(self.forward())  # consume '='
                value_node = res.register(self.expression())
                if res.error:
                    return res
                return res.success(
                    PropertyAssignNode(lhs.node, lhs.property_name_token, value_node)
                )

        self.token_index = saved_index
        self.current_token = saved_token
        self.depth = saved_depth

        return self.expression()

    def statements(self):
        res = ParserResults()
        statement_list = []

        while self.current_token.type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
            res.register_forward()
            self.forward()

        if self.current_token.type in (TOKEN_EOF, TOKEN_RCURLY):
            return res.success(StatementsNode([]))

        stmt = res.register(self.statement())
        if res.error:
            return res
        statement_list.append(stmt)

        while True:
            newline_count = 0
            while self.current_token.type in (TOKEN_NEWLINE, TOKEN_SEMICOLON):
                res.register_forward()
                self.forward()
                newline_count += 1

            if self.current_token.type in (TOKEN_EOF, TOKEN_RCURLY):
                break

            if newline_count == 0:
                previous_is_rcurly = (
                    self.token_index > 0
                    and self.tokens[self.token_index - 1].type == TOKEN_RCURLY
                )
                if not previous_is_rcurly:
                    break

            stmt = res.register(self.statement())
            if res.error:
                return res
            statement_list.append(stmt)

        return res.success(StatementsNode(statement_list))

    @_with_recursion_headroom
    def parser(self):
        try:
            res = self.statements()
        except ParseDepthExceeded:
            return ParserResults().failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN033",
                )
            )
        if not res.error and self.current_token.type != TOKEN_EOF:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN034",
                )
            )
        return res

    def block(self):
        self._depth_enter()
        try:
            return self._block()
        finally:
            self._depth_exit()

    def _block(self):
        res = ParserResults()

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN035",
                )
            )

        lcurly_pos = self.current_token.pos_start
        res.register_forward()
        self.forward()

        statements_node = res.register(self.statements())
        if res.error:
            return res

        if self.current_token.type != TOKEN_RCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN036",
                )
            )

        rcurly_pos = self.current_token.pos_end
        if not statements_node.statement_nodes:
            statements_node.pos_start = lcurly_pos
            statements_node.pos_end = rcurly_pos

        res.register_forward()
        self.forward()

        return res.success(statements_node)

    def increment_or_decrement(self):
        res = ParserResults()

        # Prefix ++i or --i
        if self.current_token.type in (TOKEN_INC, TOKEN_DEC):
            op_tok = self.current_token
            res.register_forward()
            self.forward()

            if self.current_token.type != TOKEN_IDENTIFIER:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN037",
                    )
                )

            var_tok = self.current_token
            res.register_forward()
            self.forward()
            return res.success(IncrementNode(var_tok, op_tok, is_postfix=False))

        return res.failure(
            B_SharpSyntaxError(
                self.current_token.pos_start,
                self.current_token.pos_end,
                "SYN038",
            )
        )

    def while_expression(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "while"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN039",
                )
            )

        res.register_forward()
        self.forward()

        condition = res.register(self.expression())
        if res.error:
            return res

        if self.current_token.type == TOKEN_LCURLY:
            body = res.register(self.block())
        elif self.current_token.matches(TOKEN_KEYWORD, "then"):
            res.register_forward()
            self.forward()
            body = res.register(self.statement())
        else:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN040",
                )
            )

        if res.error:
            return res

        return res.success(WhileNode(condition, body))

    def do_expression(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "do"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN041",
                )
            )

        pos_start = self.current_token.pos_start.copy()
        res.register_forward()
        self.forward()

        if not self.current_token.type == TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN042",
                )
            )

        body = res.register(self.block())
        if res.error:
            return res

        if not self.current_token.matches(TOKEN_KEYWORD, "while"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN043",
                )
            )
        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN044",
                )
            )
        res.register_forward()
        self.forward()
        self._skip_newlines(res)
        condition = res.register(self.expression())
        if res.error:
            return res
        self._skip_newlines(res)
        if self.current_token.type != TOKEN_RPAREN:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN045",
                    )
                )
        rparen_end = self.current_token.pos_end.copy()
        res.register_forward()
        self.forward()

        return res.success(DoNode(body, condition, pos_start, rparen_end))

    def for_expression(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "for"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN046",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN047",
                )
            )

        res.register_forward()
        self.forward()

        init_node = res.register(self.statement())
        if res.error:
            return res

        if self.current_token.type != TOKEN_SEMICOLON:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN048",
                )
            )

        res.register_forward()
        self.forward()

        condition_node = res.register(self.expression())
        if res.error:
            return res

        if self.current_token.type != TOKEN_SEMICOLON:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN049",
                )
            )

        res.register_forward()
        self.forward()

        update_node = res.register(self.statement())
        if res.error:
            return res

        if self.current_token.type != TOKEN_RPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN050",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type == TOKEN_LCURLY:
            body_node = res.register(self.block())
        elif self.current_token.matches(TOKEN_KEYWORD, "then"):
            res.register_forward()
            self.forward()
            body_node = res.register(self.statement())
        else:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN051",
                )
            )

        if res.error:
            return res

        return res.success(ForNode(init_node, condition_node, update_node, body_node))

    def call(self):
        res = ParserResults()
        node = res.register(self.atom())
        if res.error:
            return res

        while True:
            if self.current_token.type == TOKEN_LPAREN:
                node = res.register(self.finish_call(node))
                if res.error:
                    return res

            elif self.current_token.type == TOKEN_LBRACKET:
                node = res.register(self.parse_index_or_slice(node))
                if res.error:
                    return res

            elif self.current_token.type == TOKEN_DOT:
                res.register_forward()
                self.forward()
                if self.current_token.type != TOKEN_IDENTIFIER:
                    return res.failure(
                        B_SharpSyntaxError(
                            self.current_token.pos_start,
                            self.current_token.pos_end,
                            "SYN052",
                        )
                    )
                property_tok = self.current_token
                res.register_forward()
                self.forward()

                if self.current_token.type == TOKEN_LPAREN:
                    node = res.register(self.finish_method_call(node, property_tok))
                    if res.error:
                        return res
                else:
                    node = PropertyAccessNode(node, property_tok)
            else:
                break
        return res.success(node)

    def parse_index_or_slice(self, node):
        res = ParserResults()
        res.register_forward()
        self.forward()  # skip '['

        self._skip_newlines(res)

        start_node = None
        end_node = None
        is_slice = False

        if self.current_token.type == TOKEN_DOTDOT:
            is_slice = True
            res.register_forward()
            self.forward()  # skip '..'
            self._skip_newlines(res)
            end_node = res.register(self.expression())
            if res.error:
                return res
        else:
            expr = res.register(self.expression())
            if res.error:
                return res

            self._skip_newlines(res)

            if self.current_token.type == TOKEN_DOTDOT:
                is_slice = True
                start_node = expr
                res.register_forward()
                self.forward()  # skip '..'
                self._skip_newlines(res)
                if self.current_token.type != TOKEN_RBRACKET:
                    end_node = res.register(self.expression())
                    if res.error:
                        return res
            else:
                start_node = expr

        self._skip_newlines(res)

        if self.current_token.type != TOKEN_RBRACKET:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN053",
                )
            )

        rbracket_pos = self.current_token.pos_end
        res.register_forward()
        self.forward()

        if is_slice:
            return res.success(SliceNode(node, start_node, end_node, rbracket_pos))
        else:
            return res.success(IndexAccessNode(node, start_node))

    def finish_method_call(self, object_node, method_name_tok):
        res = ParserResults()
        arg_nodes = []
        res.register_forward()
        self.forward()  # skip '('

        self._skip_newlines(res)

        if self.current_token.type == TOKEN_RPAREN:
            rparen_pos = self.current_token.pos_end
            res.register_forward()
            self.forward()
            return res.success(
                MethodCallNode(object_node, method_name_tok, arg_nodes, rparen_pos)
            )

        arg_nodes.append(res.register(self.expression()))
        if res.error:
            return res

        while self.current_token.type == TOKEN_COMMA:
            res.register_forward()
            self.forward()
            self._skip_newlines(res)
            arg_nodes.append(res.register(self.expression()))
            if res.error:
                return res

        self._skip_newlines(res)

        if self.current_token.type != TOKEN_RPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN054",
                )
            )

        rparen_pos = self.current_token.pos_end
        res.register_forward()
        self.forward()
        return res.success(
            MethodCallNode(object_node, method_name_tok, arg_nodes, rparen_pos)
        )

    def finish_call(self, node_to_call):
        res = ParserResults()
        arg_nodes = []

        res.register_forward()
        self.forward()

        self._skip_newlines(res)

        if self.current_token.type == TOKEN_RPAREN:
            rparen_pos = self.current_token.pos_end
            res.register_forward()
            self.forward()
            return res.success(CallNode(node_to_call, arg_nodes, pos_end=rparen_pos))

        arg_nodes.append(res.register(self.expression()))
        if res.error:
            return res

        while self.current_token.type == TOKEN_COMMA:
            res.register_forward()
            self.forward()
            self._skip_newlines(res)

            arg_nodes.append(res.register(self.expression()))
            if res.error:
                return res

        self._skip_newlines(res)

        if self.current_token.type != TOKEN_RPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN055",
                )
            )

        rparen_pos = self.current_token.pos_end
        res.register_forward()
        self.forward()
        return res.success(CallNode(node_to_call, arg_nodes, pos_end=rparen_pos))

    def fn_def(self):
        res = ParserResults()

        if not self.current_token.matches(
            TOKEN_KEYWORD, "fn"
        ) and not self.current_token.matches(TOKEN_KEYWORD, "function"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN056",
                )
            )

        res.register_forward()
        self.forward()

        # Name casting rule: anonymous functions are invalid
        if self.current_token.type == TOKEN_KEYWORD:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN057",
                )
            )

        if self.current_token.type != TOKEN_IDENTIFIER:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN058",
                )
            )

        var_name_tok = self.current_token
        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN059",
                )
            )

        res.register_forward()
        self.forward()
        arg_nodes = []
        seen_param_names = {var_name_tok.value}

        self._skip_newlines(res)

        if self.current_token.type == TOKEN_RPAREN:
            res.register_forward()
            self.forward()
        else:
            if self.current_token.type != TOKEN_IDENTIFIER:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN060",
                    )
                )

            param_name = self.current_token
            res.register_forward()
            self.forward()

            param_type = None
            if self.current_token.type == TOKEN_COLON:
                res.register_forward()
                self.forward()
                if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                    param_type = self.current_token
                    res.register_forward()
                    self.forward()
                    param_type, err = self._parse_array_suffix(param_type)
                    if err:
                        return res.failure(err)
                    if TYPE_MAP.get(param_type.value) is None:
                        return res.failure(
                            B_SharpSyntaxError(
                                param_type.pos_start,
                                param_type.pos_end,
                                "SYN018",
                                {"type_name": param_type.value},
                            )
                        )
                else:
                    return res.failure(
                        B_SharpSyntaxError(
                            self.current_token.pos_start,
                            self.current_token.pos_end,
                            "SYN061",
                        )
                    )

            arg_nodes.append((param_name, param_type))
            if param_name.value in seen_param_names:
                if param_name.value == var_name_tok.value:
                    return res.failure(
                        ShadowingError(
                            param_name.pos_start,
                            param_name.pos_end,
                            param_name.value,
                            var_name_tok.value,
                        )
                    )
                return res.failure(
                    B_SharpSyntaxError(
                        param_name.pos_start,
                        param_name.pos_end,
                        "SYN062",
                        {"param_name": param_name.value, "func_name": var_name_tok.value},
                    )
                )
            seen_param_names.add(param_name.value)

            while self.current_token.type == TOKEN_COMMA:
                res.register_forward()
                self.forward()
                self._skip_newlines(res)

                if self.current_token.type != TOKEN_IDENTIFIER:
                    return res.failure(
                        B_SharpSyntaxError(
                            self.current_token.pos_start,
                            self.current_token.pos_end,
                            "SYN063",
                        )
                    )

                param_name = self.current_token
                res.register_forward()
                self.forward()

                param_type = None
                if self.current_token.type == TOKEN_COLON:
                    res.register_forward()
                    self.forward()
                    if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                        param_type = self.current_token
                        res.register_forward()
                        self.forward()
                        param_type, err = self._parse_array_suffix(param_type)
                        if err:
                            return res.failure(err)
                        if TYPE_MAP.get(param_type.value) is None:
                            return res.failure(
                                B_SharpSyntaxError(
                                    param_type.pos_start,
                                    param_type.pos_end,
                                    "SYN018",
                                    {"type_name": param_type.value},
                                )
                            )
                    else:
                        return res.failure(
                            B_SharpSyntaxError(
                                self.current_token.pos_start,
                                self.current_token.pos_end,
                                "SYN061",
                            )
                        )

                arg_nodes.append((param_name, param_type))
                if param_name.value in seen_param_names:
                    if param_name.value == var_name_tok.value:
                        return res.failure(
                            ShadowingError(
                                param_name.pos_start,
                                param_name.pos_end,
                                param_name.value,
                                var_name_tok.value,
                            )
                        )
                    return res.failure(
                        B_SharpSyntaxError(
                            param_name.pos_start,
                            param_name.pos_end,
                            "SYN062",
                            {"param_name": param_name.value, "func_name": var_name_tok.value},
                        )
                    )
                seen_param_names.add(param_name.value)

            self._skip_newlines(res)

            if self.current_token.type != TOKEN_RPAREN:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN063",
                    )
                )

            res.register_forward()
            self.forward()

        return_type_tok = None
        if self.current_token.type == TOKEN_ARROW:
            res.register_forward()
            self.forward()

            if self.current_token.type in (TOKEN_KEYWORD, TOKEN_IDENTIFIER):
                return_type_tok = self.current_token
                res.register_forward()
                self.forward()
                return_type_tok, err = self._parse_array_suffix(return_type_tok)
                if err:
                    return res.failure(err)
                if TYPE_MAP.get(return_type_tok.value) is None:
                    return res.failure(
                        B_SharpSyntaxError(
                            return_type_tok.pos_start,
                            return_type_tok.pos_end,
                            "SYN064",
                            {"return_type": return_type_tok.value},
                        )
                    )
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN065",
                    )
                )

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN066",
                )
            )

        body_node = res.register(self.block())
        if res.error:
            return res

        return res.success(
            FunctionDefNode(var_name_tok, arg_nodes, return_type_tok, body_node)
        )

    def return_statement(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "return"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN067",
                )
            )

        start_pos = self.current_token.pos_start.copy()
        end_pos = self.current_token.pos_end.copy()

        res.register_forward()
        self.forward()

        if self.current_token.type in (
            TOKEN_NEWLINE,
            TOKEN_SEMICOLON,
            TOKEN_RCURLY,
            TOKEN_EOF,
        ):
            return res.success(ReturnNode(None, start_pos, end_pos))

        expr = res.register(self.expression())
        if res.error:
            return res

        return res.success(ReturnNode(expr, start_pos, expr.pos_end))

    def struct_def(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "struct"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN070",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type == TOKEN_KEYWORD:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN057",
                )
            )

        if self.current_token.type != TOKEN_IDENTIFIER:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN071",
                )
            )

        name_tok = self.current_token
        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "SYN072",
                )
            )

        res.register_forward()
        self.forward()

        self._skip_newlines(res)

        member_nodes = []
        while self.current_token.type != TOKEN_RCURLY:
            if self.current_token.type == TOKEN_EOF:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "SYN036",
                    )
                )

            stmt = res.register(self.statement())
            if res.error:
                return res
            # Only var/const allowed inside struct (C-style) – includes MultiVariableAssignNode for `var a, b: Type`
            if not isinstance(stmt, (VariableAssignNode, MultiVariableAssignNode)):
                return res.failure(
                    B_SharpSyntaxError(
                        stmt.pos_start,
                        stmt.pos_end,
                        "SYN073",
                    )
                )
            member_nodes.append(stmt)

            self._skip_newlines(res)

        pos_end = self.current_token.pos_end
        res.register_forward()
        self.forward()

        return res.success(StructDefNode(name_tok, member_nodes, pos_end))
