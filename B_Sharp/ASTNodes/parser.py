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
                    "Expected ')'",
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
                f"Expected int, float, identifier, '+', '-', '(', or keyword, got '{tok}'",
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
                    "Expected 'using' keyword to import a module",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_STRING:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Module import name is expected to be a valid string file path",
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
                    f"Module '{file_path_str}' cannot be found.",
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
                    "Expected 'if'",
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
                    "Expected 'then' or '{' after if condition.",
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
                        "Expected 'then' or '{' after elif condition.",
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
                        "Chained comparisons are not supported. "
                        "Combine separate comparisons with 'and' or 'or'.",
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
                    "Expected ']' after type in array declaration.",
                )
            self.forward()
            if type_tok.value == "List":
                return None, B_SharpSyntaxError(
                    type_tok.pos_start,
                    type_tok.pos_end,
                    "Array of List is not supported. Use List for untyped collections.",
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
                    "Expected variable identifier name after 'var' or 'const'.",
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
                        "Expected identifier name after ','.",
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
                        "Expected type identifier after ':'.",
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
                        f"Unknown data type '{type_tok.value}'. "
                        f"{_VALID_TYPES_MESSAGE}",
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
                        "Multiple initializers in assignment are not supported.",
                    )
                )

        if is_const and type_tok is None and value_node is None:
            return res.failure(
                B_SharpSyntaxError(
                    start_tok.pos_start,
                    self.current_token.pos_end,
                    "Uninitialized 'const' declaration requires a value or type.",
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
                    "Expected '[' for creating a list.",
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
                        f"Expected a valid node inside list. Got unexpected {self.current_token}",
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
                        f"Expected ',' or ']' for a list definition. Got {self.current_token}",
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
                    "Expected '{' after 'try'.",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type == TOKEN_RCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Empty 'try' block is not allowed — it must contain at least one statement.",
                )
            )

        body_node = res.register(self.statements())
        if res.error:
            return res

        if self.current_token.type != TOKEN_RCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '}' at end of 'try' block.",
                )
            )

        rcurly_pos = self.current_token.pos_end.copy()
        res.register_forward()
        self.forward()

        if self.current_token.matches(TOKEN_KEYWORD, "catch"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Unimplemented or unfound 'catch' block after 'try'.",
                )
            )

        return res.success(TryNode(pos_start, rcurly_pos, body_node))

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
                    f"Expression or block nesting exceeds the maximum depth of {MAX_PARSE_DEPTH}.",
                )
            )
        if not res.error and self.current_token.type != TOKEN_EOF:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Unexpected token or invalid syntax.",
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
                    "Expected '{'",
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
                    "Expected '}'",
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
                        "Expected variable identifier after '++' or '--'.",
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
                "Invalid increment/decrement expression.",
            )
        )

    def while_expression(self):
        res = ParserResults()

        if not self.current_token.matches(TOKEN_KEYWORD, "while"):
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected 'while'",
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
                    "Expected '{' or 'then' after while condition.",
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
                    "Expected 'do'",
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
                    "Expected '{' after 'do' statement.",
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
                    "Expected 'while' after 'do' block.",
                )
            )
        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '(' after 'while' in do/while.",
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
                    "Expected ')' after do/while condition.",
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
                    "Expected 'for'",
                )
            )

        res.register_forward()
        self.forward()

        if self.current_token.type != TOKEN_LPAREN:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '(' after 'for'.",
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
                    "Expected ';' after for loop initializer.",
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
                    "Expected ';' after for loop condition.",
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
                    "Expected ')' after for loop header.",
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
                    "Expected '{' or 'then' after for loop expression.",
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
                            "Expected property or method name",
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
                    "Expected closing brackets ']'",
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
                    "Expected ')' or ','",
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
                    "Expected ',' or ')'",
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
                    "Expected 'fn' or 'function'",
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
                    "Unallowed calling of a function by a keyword.",
                )
            )

        if self.current_token.type != TOKEN_IDENTIFIER:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    f"Expected function identifier after function name.\n"
                    "Anonymous functions are not allowed.",
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
                    "Expected '(' after function name.",
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
                        "Expected parameter name identifier.",
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
                                f"Unknown data type '{param_type.value}'. "
                                + _VALID_TYPES_MESSAGE,
                            )
                        )
                else:
                    return res.failure(
                        B_SharpSyntaxError(
                            self.current_token.pos_start,
                            self.current_token.pos_end,
                            "Expected type identifier after ':'.",
                        )
                    )

            arg_nodes.append((param_name, param_type))
            if param_name.value in seen_param_names:
                if param_name.value == var_name_tok.value:
                    return res.failure(
                        ShadowingError(
                            param_name.pos_start,
                            param_name.pos_end,
                            f"Parameter name '{param_name.value}' shadows the function name '{var_name_tok.value}'.",
                        )
                    )
                return res.failure(
                    B_SharpSyntaxError(
                        param_name.pos_start,
                        param_name.pos_end,
                        f"Duplicate parameter name '{param_name.value}' in function '{var_name_tok.value}'.",
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
                            "Expected parameter name identifier after ','.",
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
                                    f"Unknown data type '{param_type.value}'. "
                                    + _VALID_TYPES_MESSAGE,
                                )
                            )
                    else:
                        return res.failure(
                            B_SharpSyntaxError(
                                self.current_token.pos_start,
                                self.current_token.pos_end,
                                "Expected type identifier after ':'.",
                            )
                        )

                arg_nodes.append((param_name, param_type))
                if param_name.value in seen_param_names:
                    if param_name.value == var_name_tok.value:
                        return res.failure(
                            ShadowingError(
                                param_name.pos_start,
                                param_name.pos_end,
                                f"Parameter name '{param_name.value}' shadows the function name '{var_name_tok.value}'.",
                            )
                        )
                    return res.failure(
                        B_SharpSyntaxError(
                            param_name.pos_start,
                            param_name.pos_end,
                            f"Duplicate parameter name '{param_name.value}' in function '{var_name_tok.value}'.",
                        )
                    )
                seen_param_names.add(param_name.value)

            self._skip_newlines(res)

            if self.current_token.type != TOKEN_RPAREN:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected ',' or ')' in parameter list.",
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
                            f"Unknown return type '{return_type_tok.value}'. "
                            + _VALID_TYPES_MESSAGE,
                        )
                    )
            else:
                return res.failure(
                    B_SharpSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        "Expected return type identifier after '->'.",
                    )
                )

        if self.current_token.type != TOKEN_LCURLY:
            return res.failure(
                B_SharpSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    "Expected '{' to start function body block.",
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
                    "Expected 'return'",
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


class RunTimeResult:
    def __init__(self):
        self.error = None
        self.value = None
        self.func_return_value = None
        self.should_break = False
        self.should_continue = False

    def register(self, res):
        if isinstance(res, RunTimeResult):
            if res.error:
                self.error = res.error
            if res.func_return_value is not None:
                self.func_return_value = res.func_return_value
            if res.should_break:
                self.should_break = True
            if res.should_continue:
                self.should_continue = True
            return res.value
        return res

    def success(self, value):
        self.value = value
        return self

    def success_return(self, value):
        self.func_return_value = value
        return self

    def success_break(self, value):
        self.value = value
        self.should_break = True
        return self

    def success_continue(self, value):
        self.value = value
        self.should_continue = True
        return self

    def failure(self, error):
        self.error = error
        return self


class Interpreter:
    def __init__(self, max_call_depth=500):
        self.max_call_depth = max_call_depth
        self.current_call_depth = 0
        self.loaded_modules = {}
        self.loading_modules = set()

    def _inside_function(self, context):
        current = context
        while current is not None:
            if getattr(current, "in_function", False):
                return True
            current = current.parent
        return False

    def _inside_loop(self, context):
        cur = context
        while cur is not None:
            if getattr(cur, "in_loop", False):
                return True
            if getattr(cur, "in_function", False):
                return False
            cur = cur.parent

        return False

    @_with_recursion_headroom
    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        return RunTimeResult().failure(
            RunTimeError(
                getattr(node, "pos_start", None),
                getattr(node, "pos_end", None),
                f"No visitor implemented for node '{type(node).__name__}'.",
            )
        )

    ################################################################
    # Visitors
    ################################################################

    def visit_NumberNode(self, node, context):
        return RunTimeResult().success(
            Number(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_BooleanNode(self, node, context):
        value = node.token.value == "true"
        return RunTimeResult().success(
            Boolean(value).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_NoneNode(self, node, context):
        return RunTimeResult().success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_ListNode(self, node, context):
        res = RunTimeResult()
        list_of_elements = []

        for element_node in node.list_of_expressions:
            list_of_elements.append(res.register(self.visit(element_node, context)))

            if res.error:
                return res

        return res.success(
            List(list_of_elements)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_BinaryOpNode(self, node, context):
        res = RunTimeResult()
        left = res.register(self.visit(node.left_node, context))
        if res.error:
            return res

        # 'and'/'or' short-circuit: the right operand is only evaluated when
        # the result can still change.
        if node.op_token.type == TOKEN_KEYWORD and node.op_token.value in (
            "and",
            "or",
        ):
            return self.visit_short_circuit(node, left, res, context)

        right = res.register(self.visit(node.right_node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_PLUS:
            result, error = left.addition(right)
        elif node.op_token.type == TOKEN_MINUS:
            result, error = left.subtraction(right)
        elif node.op_token.type == TOKEN_MUL:
            result, error = left.multiplication(right)
            if error and hasattr(right, "_reversed_multiplication"):
                result, error = right._reversed_multiplication(left)
        elif node.op_token.type == TOKEN_DIV:
            result, error = left.division(right)
        elif node.op_token.type == TOKEN_IDIV:
            result, error = left.integer_division(right)
        elif node.op_token.type == TOKEN_POWER:
            result, error = left.power(right)
        elif node.op_token.type == TOKEN_EE:
            result, error = left.is_equal(right)
        elif node.op_token.type == TOKEN_NOT_E:
            result, error = left.not_equal(right)
        elif node.op_token.type == TOKEN_LT:
            result, error = left.less_than(right)
        elif node.op_token.type == TOKEN_GT:
            result, error = left.greater_than(right)
        elif node.op_token.type == TOKEN_LTE:
            result, error = left.less_than_equal(right)
        elif node.op_token.type == TOKEN_GTE:
            result, error = left.greater_than_equal(right)
        elif node.op_token.type == TOKEN_MODULO:
            result, error = left.modulo_division(right)
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                f"Unknown binary operator '{node.op_token.value or node.op_token.type}'.",
            )

        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_short_circuit(self, node, left, res, context):
        is_and = node.op_token.value == "and"

        if isinstance(left, Boolean):
            if is_and:
                if left.value:
                    right = res.register(self.visit(node.right_node, context))
                    if res.error:
                        return res
                    result, error = left.and_(right)
                else:
                    result, error = Boolean(False), None
            else:
                if left.value:
                    result, error = Boolean(True), None
                else:
                    right = res.register(self.visit(node.right_node, context))
                    if res.error:
                        return res
                    result, error = left.or_(right)
        else:
            result, error = left.and_(left) if is_and else left.or_(left)

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RunTimeResult()
        operand = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_MINUS:
            if isinstance(operand, Inf):
                # Negating infinity flips its sign instead of falling
                # through the multiplication path.
                result, error = operand.negated(), None
            elif isinstance(operand, (Number, List, Array)):
                result, error = operand.multiplication(Number(-1))
            else:
                result, error = None, RunTimeError(
                    node.op_token.pos_start,
                    node.pos_end,
                    f"Unary '-' cannot negate {type(operand).__name__}. "
                    "Only Number, list/array, and inf values can be negated.",
                )
        elif node.op_token.type == TOKEN_PLUS:
            result, error = operand, None
        elif node.op_token.type == TOKEN_KEYWORD and node.op_token.value == "not":
            result, error = operand.not_()
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                f"Unknown unary operator '{node.op_token.value}'.",
            )

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_VariableAccessNode(self, node, context):
        result = RunTimeResult()
        var_name = node.name.value
        value, error = context.variables.set_pos(node.pos_start, node.pos_end).get(
            var_name
        )

        if error:
            return result.failure(error)
        return result.success(value)

    def visit_VariableAssignNode(self, node, context):
        res = RunTimeResult()
        var_name = node.name.value

        is_implicit = node.value is None

        data_type_class = None
        if node.data_type:
            data_type_class = TYPE_MAP.get(node.data_type.value)

        if is_implicit:
            # Fallback per Docs/1_Common/2_data_types.md:136
            value = default_for_type(
                data_type_class, node.pos_start, node.pos_end, context
            )
        else:
            value = res.register(self.visit(node.value, context))
            if res.error:
                return res

        if (
            data_type_class
            and issubclass(data_type_class, Array)
            and isinstance(value, List)
        ):
            array_class = TYPE_MAP.get(node.data_type.value)
            if array_class:
                value = array_class(value.list_of_elements)
                value.set_context(context).set_pos(node.pos_start, node.pos_end)
                err = value._validate_all()
                if err:
                    return res.failure(err)

        # Fix 3: alias bug — List/Array assignment must copy (deep) to avoid mutating original
        if isinstance(value, (List, Array)):
            value = value.copy()

        val, error = context.variables.set_pos(node.pos_start, node.pos_end).define(
            name=var_name,
            data_type=data_type_class,
            value=value,
            is_const=node.is_const,
        )

        if error:
            return res.failure(error)
        return res.success(val)

    def visit_MultiVariableAssignNode(self, node, context):
        res = RunTimeResult()

        is_implicit = node.value is None

        data_type_class = None
        if node.data_type:
            data_type_class = TYPE_MAP.get(node.data_type.value)

        if is_implicit:
            # Fallback per Docs/1_Common/2_data_types.md:136
            value = default_for_type(
                data_type_class, node.names[0].pos_start, node.pos_end, context
            )
        else:
            value = res.register(self.visit(node.value, context))
            if res.error:
                return res

        if (
            data_type_class
            and issubclass(data_type_class, Array)
            and isinstance(value, List)
        ):
            array_class = TYPE_MAP.get(node.data_type.value)
            if array_class:
                value = array_class(value.list_of_elements)
                value.set_context(context).set_pos(node.pos_start, node.pos_end)
                err = value._validate_all()
                if err:
                    return res.failure(err)

        last_val = value
        for name_tok in node.names:
            var_name = name_tok.value
            assigned_value = value.copy() if isinstance(value, (List, Array)) else value
            val, error = context.variables.set_pos(
                name_tok.pos_start, name_tok.pos_end
            ).define(
                name=var_name,
                data_type=data_type_class,
                value=assigned_value,
                is_const=node.is_const,
            )
            if error:
                return res.failure(error)
            last_val = val

        return res.success(last_val)

    def visit_VariableReassignNode(self, node, context):
        res = RunTimeResult()
        var_name = node.name.value

        value = res.register(self.visit(node.value, context))
        if res.error:
            return res

        declared_type, err = context.variables.get_type(
            var_name, node.pos_start, node.pos_end
        )
        if err:
            return res.failure(err)

        if (
            declared_type
            and issubclass(declared_type, Array)
            and isinstance(value, List)
        ):
            for key, arr_class in TYPE_MAP.items():
                if arr_class is declared_type:
                    value = arr_class(value.list_of_elements)
                    value.set_context(context).set_pos(node.pos_start, node.pos_end)
                    val_err = value._validate_all()
                    if val_err:
                        return res.failure(val_err)
                    break

        # Fix 3: reassignment alias — copy List/Array to keep variable independence
        if isinstance(value, (List, Array)):
            value = value.copy()

        val, error = context.variables.set_pos(node.pos_start, node.pos_end).assign(
            name=var_name, value=value
        )

        if error:
            return res.failure(error)
        return res.success(val)

    def visit_IfNode(self, node, context):
        res = RunTimeResult()

        for condition, expression in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.error:
                return res
            if res.should_break or res.should_continue:
                return res
            if res.func_return_value is not None:
                return res

            if condition_value.true_():
                # Leaking: `var` inside `if` must be visible outside (no new Context)
                expression_value = res.register(self.visit(expression, context))
                if res.error:
                    return res
                if res.should_break or res.should_continue:
                    return res
                if res.func_return_value is not None:
                    return res
                return res.success(expression_value)

        if node.else_case:
            else_value = res.register(self.visit(node.else_case, context))
            if res.error:
                return res
            if res.should_break or res.should_continue:
                return res
            if res.func_return_value is not None:
                return res
            return res.success(else_value)

        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_StatementsNode(self, node, context):
        res = RunTimeResult()
        last_value = Empty().set_context(context)

        for stmt in node.statement_nodes:
            value = res.register(self.visit(stmt, context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res
            if res.should_break or res.should_continue:
                return res
            last_value = value

        return res.success(last_value)

    def visit_StringNode(self, node, context):
        return RunTimeResult().success(
            String(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_IncrementNode(self, node, context):
        res = RunTimeResult()

        var_name = node.var_name_tok.value
        val, error = context.variables.set_pos(node.pos_start, node.pos_end).get(
            var_name
        )

        if error:
            return res.failure(error)

        if not isinstance(val, Number):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Increment/decrement operations are only supported on Number types.",
                )
            )

        old_num = val.value
        new_num = old_num + 1 if node.op_tok.type == TOKEN_INC else old_num - 1
        new_val = (
            Number(new_num).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

        _, assign_err = context.variables.set_pos(node.pos_start, node.pos_end).assign(
            var_name, new_val
        )
        if assign_err:
            return res.failure(assign_err)

        return res.success(
            Number(old_num if node.is_postfix else new_num)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_WhileNode(self, node, context):
        res = RunTimeResult()

        while True:
            cond_val = res.register(self.visit(node.condition_node, context))
            if res.error:
                return res

            if not cond_val.true_():
                break

            body_context = BodyScopeContext(
                context, context, in_function=context.in_function
            )
            val = res.register(self.visit(node.body_node, body_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res

            if res.should_break:
                res.should_break = False
                break

            if res.should_continue:
                res.should_continue = False
                continue

        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_DoNode(self, node, context):
        res = RunTimeResult()
        while True:
            body_ctx = BodyScopeContext(
                context, context, in_function=context.in_function
            )
            val = res.register(self.visit(node.body_node, body_ctx))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res
            if res.should_break:
                res.should_break = False
                break
            if res.should_continue:
                res.should_continue = False
            cond_val = res.register(self.visit(node.condition_node, context))
            if res.error:
                return res
            if res.should_break or res.should_continue:
                return res
            if res.func_return_value is not None:
                return res
            if not cond_val.true_():
                break
        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_ForNode(self, node, context):
        res = RunTimeResult()

        loop_context = Context(
            "<for>",
            context,
            node.pos_start,
            in_function=context.in_function,
            in_loop=True,
        )
        res.register(self.visit(node.init_node, loop_context))
        if res.error:
            return res

        while True:
            cond_val = res.register(self.visit(node.condition_node, loop_context))
            if res.error:
                return res

            if not cond_val.true_():
                break

            body_context = BodyScopeContext(
                loop_context, context, in_function=loop_context.in_function
            )
            val = res.register(self.visit(node.body_node, body_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res

            if res.should_break:
                res.should_break = False
                break

            if res.should_continue:
                res.should_continue = False

            res.register(self.visit(node.update_node, loop_context))
            if res.error:
                return res

        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_FunctionDefNode(self, node, context):
        res = RunTimeResult()

        func_name = node.var_name_tok.value
        body_node = node.body_node
        arg_nodes = node.arg_nodes
        return_type_tok = node.return_type_tok

        func_value = Function(
            name=func_name,
            body_node=body_node,
            arg_nodes=arg_nodes,
            return_type_tok=return_type_tok,
            parent_context=context,
        ).set_pos(node.pos_start, node.pos_end)

        # F1: if promised return type, body must guarantee a `return <value>` on all paths
        if func_value.return_type is not None:

            def _always_returns(n):
                if isinstance(n, ReturnNode):
                    return n.node_to_return is not None
                if isinstance(n, IfNode):
                    # all branches must always return and else must exist
                    if n.else_case is None:
                        return False
                    for _, expr in n.cases:
                        if not _always_returns(expr):
                            return False
                    if not _always_returns(n.else_case):
                        return False
                    return True
                if isinstance(n, StatementsNode):
                    for s in n.statement_nodes:
                        if _always_returns(s):
                            return True
                    return False
                if isinstance(n, WhileNode):
                    return False
                if isinstance(n, ForNode):
                    return False
                return False

            if not _always_returns(body_node):
                return res.failure(
                    B_SharpSyntaxError(
                        node.var_name_tok.pos_start,
                        node.var_name_tok.pos_end,
                        f"Function '{func_name}' promises return type '{func_value.return_type.__name__}' but not all code paths return a value. Ensure every branch ends with 'return <value>'.",
                    )
                )

        # Emit warnings for unreachable code after return (for any function)
        def _always_returns_for_unreachable(n):
            if isinstance(n, ReturnNode):
                return n.node_to_return is not None or True  # any return dominates
            if isinstance(n, IfNode):
                if n.else_case is None:
                    return False
                for _, expr in n.cases:
                    if not _always_returns_for_unreachable(expr):
                        return False
                return _always_returns_for_unreachable(n.else_case)
            if isinstance(n, StatementsNode):
                for s in n.statement_nodes:
                    if _always_returns_for_unreachable(s):
                        return True
                return False
            return False

        def _emit_unreachable(stmts):
            if isinstance(stmts, StatementsNode):
                seen_return = False
                for s in stmts.statement_nodes:
                    if seen_return:
                        try:
                            w = UnreachableCodeWarning(
                                s.pos_start,
                                s.pos_end,
                                f"Unreachable code after 'return' in function '{func_name}' – this statement will be ignored.",
                            )
                            print(w, end="", file=sys.stderr)
                        except Exception:
                            pass
                    # check if this statement always returns
                    if _always_returns_for_unreachable(s):
                        seen_return = True
                    # recurse into nested blocks for internal unreachable
                    if isinstance(s, IfNode):
                        for _, expr in s.cases:
                            _emit_unreachable(expr)
                        if s.else_case:
                            _emit_unreachable(s.else_case)
                    elif isinstance(s, WhileNode):
                        _emit_unreachable(s.body_node)
                    elif isinstance(s, ForNode):
                        _emit_unreachable(s.body_node)
                    elif isinstance(s, StatementsNode):
                        _emit_unreachable(s)

        try:
            _emit_unreachable(body_node)
        except Exception:
            pass

        val, error = context.variables.set_pos(node.pos_start, node.pos_end).define(
            name=func_name,
            data_type=Function,
            value=func_value,
            is_const=False,
        )

        if error:
            return res.failure(error)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RunTimeResult()

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.error:
            return res

        if not isinstance(value_to_call, (Function, BuiltinFunction)):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'{node.node_to_call}' is not a function.",
                )
            )

        args = []
        for arg_node in node.arg_nodes:
            arg_val = res.register(self.visit(arg_node, context))
            if res.error:
                return res
            args.append(arg_val)

        if isinstance(value_to_call, BuiltinFunction):
            value_to_call.set_context(context)
            value_to_call.pos_start = node.pos_start
            value_to_call.pos_end = node.pos_end
            result = res.register(
                value_to_call.execute(
                    args, self, call_pos_start=node.pos_start, call_pos_end=node.pos_end
                )
            )
            if res.error:
                return res
            return res.success(result)

        if self.current_call_depth >= self.max_call_depth:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Maximum call depth exceeded (recursion too deep).",
                )
            )

        self.current_call_depth += 1
        try:
            return_value = res.register(
                value_to_call.execute(
                    args, self, call_pos_start=node.pos_start, call_pos_end=node.pos_end
                )
            )
        finally:
            self.current_call_depth -= 1

        if res.error:
            return res

        return res.success(return_value)

    def visit_ReturnNode(self, node, context):
        res = RunTimeResult()

        if not self._inside_function(context):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot use 'return' outside of a function.",
                )
            )

        if node.node_to_return:
            return_val = res.register(self.visit(node.node_to_return, context))
            if res.error:
                return res
        else:
            return_val = (
                Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        return res.success_return(return_val)

    def visit_PropertyAccessNode(self, node, context):
        res = RunTimeResult()
        obj = res.register(self.visit(node.node, context))
        if res.error:
            return res

        _property = node.property_name_token.value
        pos = node.pos_start, node.pos_end

        # Unified size API: both .length and .size work on every
        # sized builtin type (String, List, Array).
        sized_types = (List, Array, String)
        if isinstance(obj, sized_types) and _property in ("length", "size"):
            size = (
                len(obj.value) if isinstance(obj, String) else len(obj.list_of_elements)
            )
            return res.success(Number(size).set_context(context).set_pos(*pos))

        # Typed arrays must be checked before base Array/List
        if isinstance(obj, NumberArray):
            type_name = "Number[]"
        elif isinstance(obj, StringArray):
            type_name = "String[]"
        elif isinstance(obj, BooleanArray):
            type_name = "Bool[]"
        elif isinstance(obj, EmptyArray):
            type_name = "Empty[]"
        elif isinstance(obj, Array):
            type_name = "Array"
        elif isinstance(obj, List):
            type_name = "List"
        elif isinstance(obj, String):
            type_name = "String"
        elif isinstance(obj, Number):
            type_name = "Number"
        elif isinstance(obj, Boolean):
            type_name = "Bool"
        elif isinstance(obj, Empty):
            type_name = "Empty"
        elif isinstance(obj, NaN):
            type_name = "NaN"
        elif isinstance(obj, Inf):
            type_name = "Inf"
        elif isinstance(obj, (Function, BuiltinFunction)):
            type_name = "Function"
        else:
            type_name = type(obj).__name__

        if _property == "type":
            return res.success(String(type_name).set_context(context).set_pos(*pos))

        expected = "'length' or 'size'" if isinstance(obj, sized_types) else "'type'"
        return res.failure(
            RunTimeError(
                node.pos_start,
                node.pos_end,
                f"Unexpected property '{_property}' for {obj.__class__.__name__}. "
                f"Supported properties here: {expected}.",
            )
        )

    def visit_IndexAccessNode(self, node, context):
        res = RunTimeResult()
        obj = res.register(self.visit(node.node, context))
        if res.error:
            return res

        index = res.register(self.visit(node.index_node, context))
        if res.error:
            return res

        if isinstance(obj, (List, Array)):
            i, err = self._require_int(index, node)
            if err:
                return res.failure(err)

            if i < 0:
                i += len(obj.list_of_elements)
            if i < 0 or i >= len(obj.list_of_elements):
                return res.failure(
                    RunTimeError(
                        node.pos_start, node.pos_end, "Index is out of bounds."
                    )
                )

            element = obj.list_of_elements[i]
            return res.success(
                element.set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        if isinstance(obj, String):
            i, err = self._require_int(index, node)
            if err:
                return res.failure(err)

            if i < 0:
                i += len(obj.value)
            if i < 0 or i >= len(obj.value):
                return res.failure(
                    RunTimeError(
                        node.pos_start, node.pos_end, "Index is out of bounds."
                    )
                )
            return res.success(
                String(obj.value[i])
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

        return res.failure(
            RunTimeError(node.pos_start, node.pos_end, "Given type is not indexable.")
        )

    def visit_IndexAssignNode(self, node, context):
        res = RunTimeResult()
        # Resolve the target container and index
        # target is an IndexAccessNode (possibly nested)
        target = node.target

        # We need to get the object that holds the index we assign to.
        # For `a[0][1] = v`, target is IndexAccessNode( IndexAccessNode(a,0), 1 )
        # So we visit target.node to get the inner container, then assign at target.index_node
        # For simplicity, evaluate the container chain fully:
        # Use recursion: peel off outermost index, evaluate the inner container via visit
        container_node = target.node
        index_node = target.index_node

        container = res.register(self.visit(container_node, context))
        if res.error:
            return res
        index_val = res.register(self.visit(index_node, context))
        if res.error:
            return res
        value = res.register(self.visit(node.value_node, context))
        if res.error:
            return res

        if isinstance(container, (List, Array)):
            i, err = self._require_int(index_val, node)
            if err:
                return res.failure(err)
            # assign_at handles negative wrap, dynamic growth, and const check
            _, err = container.assign_at(i, value)
            if err:
                return res.failure(err)
            return res.success(
                value.set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        if isinstance(container, String):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot assign to string index (strings are immutable).",
                )
            )

        return res.failure(
            RunTimeError(
                node.pos_start, node.pos_end, "Target of assignment is not indexable."
            )
        )

    def _resolve_slice_bounds(self, node, context, res, length):
        """Evaluates optional slice endpoints.

        Negative values wrap Python-style; out-of-range values clamp into
        [0, length]. Returns (start, end) or (None, None) after registering
        a failure on `res`.
        """
        start = 0
        if node.start_node is not None:
            start_val = res.register(self.visit(node.start_node, context))
            if res.error:
                return None, None
            start, err = self._require_int(start_val, node, "Slice start")
            if err:
                res.failure(err)
                return None, None
        else:
            start = 0

        end = length
        if node.end_node is not None:
            end_val = res.register(self.visit(node.end_node, context))
            if res.error:
                return None, None
            end, err = self._require_int(end_val, node, "Slice end")
            if err:
                res.failure(err)
                return None, None

        if start < 0:
            start += length
        if end < 0:
            end += length
        start = max(0, min(start, length))
        end = max(0, min(end, length))
        if start > end:
            start = end
        return start, end

    def visit_SliceNode(self, node, context):
        res = RunTimeResult()
        obj = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if isinstance(obj, (List, Array)):
            length = len(obj.list_of_elements)
            start, end = self._resolve_slice_bounds(node, context, res, length)
            if res.error:
                return res

            sliced = obj.list_of_elements[start:end]
            # Deep copy nested List/Array elements for full isolation
            deep_sliced = []
            for el in sliced:
                if isinstance(el, (List, Array)):
                    deep_sliced.append(el.copy())
                else:
                    deep_sliced.append(el)
            if isinstance(obj, Array):
                result = obj._new_array(deep_sliced)
            else:
                result = List(deep_sliced)
            return res.success(
                result.set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        if isinstance(obj, String):
            length = len(obj.value)
            start, end = self._resolve_slice_bounds(node, context, res, length)
            if res.error:
                return res

            return res.success(
                String(obj.value[start:end])
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

        return res.failure(
            RunTimeError(node.pos_start, node.pos_end, "Cannot slice this type.")
        )

    def _load_module(self, node, res, file_path):
        """Lexes, parses and executes a module exactly once.

        Returns the module's root Context (registered in loaded_modules)
        or None after registering a failure on `res`.
        """
        if file_path in self.loaded_modules:
            return self.loaded_modules[file_path]

        if not os.path.exists(file_path):
            res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"Could not import '{file_path}': File not found.",
                )
            )
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                script = f.read()
        except Exception as e:
            res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"Failed to read module '{file_path}': {str(e)}",
                )
            )
            return None

        from B_Sharp.lexer import Lexer

        lexer = Lexer(file_path, script)
        tokens, lexer_error = lexer.tokenize()
        if lexer_error:
            res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"Failed to tokenize module '{file_path}': {lexer_error}",
                )
            )
            return None

        module_parser = Parser(tokens)
        try:
            ast = module_parser.parser()
        except ParseDepthExceeded:
            ast = ParserResults().failure(
                B_SharpSyntaxError(
                    tokens[-1].pos_start,
                    tokens[-1].pos_end,
                    f"Module '{file_path}' exceeds the maximum nesting depth.",
                )
            )
        if ast.error:
            res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"Failed to parse module '{file_path}': {ast.error}",
                )
            )
            return None

        # The module gets its own isolated root scope: it can neither see
        # nor shadow the importer's globals.
        import_context = Context(file_path)
        register_builtins(import_context)

        self.loading_modules.add(file_path)
        interpreter = Interpreter()
        interpreter.loaded_modules = self.loaded_modules
        interpreter.loading_modules = self.loading_modules
        try:
            result = interpreter.visit(ast.node, import_context)
        finally:
            self.loading_modules.discard(file_path)

        if result.error:
            res.failure(result.error)
            return None

        self.loaded_modules[file_path] = import_context
        return import_context

    def _module_exports(self, module_context):
        """Names exported by a module: everything except builtins."""
        return {
            name: entry
            for name, entry in module_context.variables.variables.items()
            if not isinstance(entry["value"], BuiltinFunction)
        }

    def visit_ImportNode(self, node, context):
        res = RunTimeResult()
        file_path = node.module_to_import
        symbols_to_import = node.symbols  # None or list of names

        if file_path in self.loading_modules:
            return res.failure(
                CircularImportError(
                    node.pos_start,
                    node.pos_end,
                    f"Circular import detected: '{file_path}' is already being loaded.",
                )
            )

        module_context = self._load_module(node, res, file_path)
        if module_context is None:
            return res

        exports = self._module_exports(module_context)

        # Two-pass: validate every requested symbol before injecting any,
        # so a failure never leaves partially imported state.
        if symbols_to_import is not None:
            missing = [s for s in symbols_to_import if s not in exports]
            if missing:
                return res.failure(
                    RunTimeError(
                        node.pos_start,
                        node.pos_end,
                        f"Symbol(s) {', '.join(repr(s) for s in missing)} "
                        f"not found in module '{file_path}'.",
                    )
                )
            selected = {s: exports[s] for s in symbols_to_import}
        else:
            selected = exports

        # Inject copies of the entries through define(), so existing local
        # variables, consts, and builtins are protected from overwrite and
        # the importer never shares mutable binding state with the module.
        for name, entry in selected.items():
            value = entry["value"]
            if hasattr(value, "copy") and isinstance(value, (List, Array)):
                value = value.copy()
            _, error = context.variables.set_pos(node.pos_start, node.pos_end).define(
                name=name,
                data_type=entry["type"],
                value=value,
                is_const=entry["is_const"],
            )
            if error:
                return res.failure(error)

        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_NaNNode(self, node, context):
        res = RunTimeResult()
        return res.success(
            NaN().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_InfinityNode(self, node, context):
        return RunTimeResult().success(
            Inf().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def _require_int(self, value, node, label="Index"):
        """Converts a runtime Number to a Python int.

        Booleans and floats are rejected; integers pass through.
        Returns (int, None) or (None, error).
        """
        if not isinstance(value, Number) or isinstance(value.value, float):
            return None, RunTimeError(
                node.pos_start,
                node.pos_end,
                f"{label} must be an integer Number.",
            )
        return int(value.value), None

    def visit_MethodCallNode(self, node, context):
        res = RunTimeResult()
        obj = res.register(self.visit(node.object_node, context))
        if res.error:
            return res

        method_name = node.method_name_tok.value
        args = []
        for arg in node.arg_nodes:
            arg_val = res.register(self.visit(arg, context))
            if res.error:
                return res
            args.append(arg_val)

        if not isinstance(obj, (List, Array)):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'{method_name}' is not a method of {obj.__class__.__name__}",
                )
            )

        arities = {
            "push": (1, 2),
            "append": (1, 1),
            "swap": (2, 2),
            "delete": (1, 1),
            "drop": (2, 2),
        }
        if method_name not in arities:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'{method_name}' is not a method of {obj.__class__.__name__}. "
                    "Supported methods: push, append, swap, delete, drop.",
                )
            )

        lo, hi = arities[method_name]
        if not (lo <= len(args) <= hi):
            expected = str(lo) if lo == hi else f"{lo} to {hi}"
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'{method_name}' expects {expected} argument(s), got {len(args)}.",
                )
            )

        # All mutating methods operate on the SAME list/array object.
        # Only 'drop' returns a value: the extracted slice as a new List.
        if method_name == "push":
            index = None
            if len(args) == 2:
                index, err = self._require_int(args[1], node)
                if err:
                    return res.failure(err)
            _, error = obj.push(args[0], index)
        elif method_name == "append":
            _, error = obj.append(args[0])
        elif method_name == "swap":
            index, err = self._require_int(args[1], node)
            if err:
                return res.failure(err)
            _, error = obj.swap(args[0], index)
        elif method_name == "delete":
            index, err = self._require_int(args[0], node)
            if err:
                return res.failure(err)
            _, error = obj.delete(index)
        else:  # drop
            start, err = self._require_int(args[0], node, "Slice start")
            if err:
                return res.failure(err)
            end, err = self._require_int(args[1], node, "Slice end")
            if err:
                return res.failure(err)
            removed, error = obj.drop(start, end)
            if error:
                return res.failure(error)
            return res.success(
                removed.set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        if error:
            return res.failure(error)
        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_PassNode(self, node, context):
        return RunTimeResult().success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_BreakNode(self, node, context):
        res = RunTimeResult()
        if not self._inside_loop(context):
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "'break' outside loop.")
            )
        res.should_break = True
        res.value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        return res

    def visit_ContinueNode(self, node, context):
        res = RunTimeResult()
        if not self._inside_loop(context):
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "'continue' outside loop.")
            )
        res.should_continue = True
        res.value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        return res

    def visit_TryNode(self, node, context):
        res = RunTimeResult()

        # Leaking: `var` inside `try` must be visible outside (same context, no isolation)
        res.register(self.visit(node.body_node, context))
        if res.error:
            return res
        if res.func_return_value is not None:
            return res
        if res.should_break or res.should_continue:
            return res

        return res.success(
            Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        )
