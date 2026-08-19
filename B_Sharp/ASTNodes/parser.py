import sys

from B_Sharp.tokens import *
from B_Sharp.errors import *
from B_Sharp.ASTNodes.instances import *
from B_Sharp.ASTNodes.nodes import *
from B_Sharp.builtins import BuiltinFunction


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
        self.forward()

    def forward(self):
        self.token_index += 1
        if self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]
        return self.current_token

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
            expr = res.register(self.expression())
            if res.error:
                return res
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

        elif tok.type == TOKEN_LBRACKET:
            list_expression = res.register(self.make_list())
            if res.error:
                return res

            return res.success(list_expression)

        return res.failure(
            B_SharpSyntaxError(
                tok.pos_start,
                tok.pos_end,
                f"Expected int, float, identifier, '+', '-', '(', or keyword, got '{tok}'",
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

        if self.current_token.type == TOKEN_RBRACKET:
            res.register_forward()
            self.forward()

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

                list_of_elements.append(res.register(self.expression()))
                if res.error:
                    return res

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

    def factor(self):
        return self.binary_operation(self.unary, (TOKEN_MUL, TOKEN_DIV, TOKEN_IDIV))

    def term(self):
        return self.binary_operation(self.factor, (TOKEN_PLUS, TOKEN_MINUS))

    def comparison(self):
        return self.binary_operation(
            self.term,
            (TOKEN_EE, TOKEN_NOT_E, TOKEN_LT, TOKEN_GT, TOKEN_LTE, TOKEN_GTE),
        )

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
                        f"Valid types: number, boolean, complex, string, empty.",
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

    def statement(self):
        res = ParserResults()

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
            elif self.current_token.value == "for":
                return self.for_expression()

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
                # A closing brace terminates a block statement, so the next
                # statement may begin on the same line ('} stmt;').
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

    def parser(self):
        res = self.statements()
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

        # 1. Initializer: var i = 0 or i = 0
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

        # 2. Condition: i < 10
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

        # 3. Update expression: i++ / ++i / i = i + 1
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

        # 4. Body: { ... } or then statement
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

        start_node = None
        end_node = None
        is_slice = False

        if self.current_token.type == TOKEN_DOTDOT:
            is_slice = True
            res.register_forward()
            self.forward()  # skip '..'
            end_node = res.register(self.expression())
            if res.error:
                return res
        else:
            expr = res.register(self.expression())
            if res.error:
                return res

            if self.current_token.type == TOKEN_DOTDOT:
                is_slice = True
                start_node = expr
                res.register_forward()
                self.forward()  # skip '..'
                if self.current_token.type != TOKEN_RBRACKET:
                    end_node = res.register(self.expression())
                    if res.error:
                        return res
            else:
                start_node = expr

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
            arg_nodes.append(res.register(self.expression()))
            if res.error:
                return res

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

            arg_nodes.append(res.register(self.expression()))
            if res.error:
                return res

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
        seen_param_names = set()

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
                                f"Unknown data type '{param_type.value}'.",
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
                                    f"Unknown data type '{param_type.value}'.",
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
                    return res.failure(
                        B_SharpSyntaxError(
                            param_name.pos_start,
                            param_name.pos_end,
                            f"Duplicate parameter name '{param_name.value}' in function '{var_name_tok.value}'.",
                        )
                    )
                seen_param_names.add(param_name.value)

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
                            f"Unknown return type '{return_type_tok.value}'.",
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

    def register(self, res):
        if isinstance(res, RunTimeResult):
            if res.error:
                self.error = res.error
            if res.func_return_value is not None:
                self.func_return_value = res.func_return_value
            return res.value
        return res

    def success(self, value):
        self.value = value
        return self

    def success_return(self, value):
        self.func_return_value = value
        return self

    def failure(self, error):
        self.error = error
        return self


class Interpreter:
    def __init__(self, max_call_depth=500):
        self.max_call_depth = max_call_depth
        self.current_call_depth = 0
        if sys.getrecursionlimit() < 10000:
            sys.setrecursionlimit(10000)

    def _inside_function(self, context):
        current = context
        while current is not None:
            if getattr(current, "in_function", False):
                return True
            current = current.parent
        return False

    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")

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
            result, error = operand.multiplication(Number(-1))
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

    def visit_BinaryNegationNode(self, node, context):
        res = RunTimeResult()
        operand = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if node.op_token.type == TOKEN_MINUS:
            result, error = operand.multiplication(Number(-1))
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                f"Unknown binary negation operator '{node.op_token.value}'.",
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

        if node.value:
            value = res.register(self.visit(node.value, context))
            if res.error:
                return res
        else:
            value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)

        data_type_class = None
        if node.data_type:
            data_type_class = TYPE_MAP.get(node.data_type.value)

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

        if node.value:
            value = res.register(self.visit(node.value, context))
            if res.error:
                return res
        else:
            value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)

        data_type_class = None
        if node.data_type:
            data_type_class = TYPE_MAP.get(node.data_type.value)

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
            val, error = context.variables.set_pos(
                name_tok.pos_start, name_tok.pos_end
            ).define(
                name=var_name,
                data_type=data_type_class,
                value=value,
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

            if condition_value.true_():
                branch_context = Context("<if>", context, node.pos_start)
                expression_value = res.register(self.visit(expression, branch_context))
                if res.error:
                    return res
                if res.func_return_value is not None:
                    return res
                return res.success(expression_value)

        if node.else_case:
            branch_context = Context("<if>", context, node.pos_start)
            else_value = res.register(self.visit(node.else_case, branch_context))
            if res.error:
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
        elements = []

        while True:
            cond_val = res.register(self.visit(node.condition_node, context))
            if res.error:
                return res

            if not cond_val.true_():
                break

            body_context = Context("<while>", context, node.pos_start)
            val = res.register(self.visit(node.body_node, body_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res

            elements.append(val)

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_ForNode(self, node, context):
        res = RunTimeResult()
        elements = []

        loop_context = Context("<for>", context, node.pos_start)
        res.register(self.visit(node.init_node, loop_context))
        if res.error:
            return res

        while True:
            cond_val = res.register(self.visit(node.condition_node, loop_context))
            if res.error:
                return res

            if not cond_val.true_():
                break

            body_context = Context("<for>", loop_context, node.pos_start)
            val = res.register(self.visit(node.body_node, body_context))
            if res.error:
                return res
            if res.func_return_value is not None:
                return res

            elements.append(val)

            res.register(self.visit(node.update_node, loop_context))
            if res.error:
                return res

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
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
                value_to_call.execute(args, self, call_pos_start=node.pos_start, call_pos_end=node.pos_end)
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

        if isinstance(obj, (List, Array)):
            if _property == "length":
                return res.success(
                    Number(len(obj.list_of_elements)).set_context(context).set_pos(*pos)
                )
            if _property == "type":
                return res.success(
                    String(obj.__class__.__name__).set_context(context).set_pos(*pos)
                )

        if isinstance(obj, String):
            if _property == "size":
                return res.success(
                    Number(len(obj.value)).set_context(context).set_pos(*pos)
                )
            if _property == "type":
                return res.success(
                    String("String").set_context(context).set_pos(*pos)
                )

        if isinstance(obj, Number):
            if _property == "type":
                return res.success(
                    String("Number").set_context(context).set_pos(*pos)
                )

        if isinstance(obj, Boolean):
            if _property == "type":
                return res.success(
                    String("Bool").set_context(context).set_pos(*pos)
                )

        if isinstance(obj, Empty):
            if _property == "type":
                return res.success(
                    String("Empty").set_context(context).set_pos(*pos)
                )

        return res.failure(
            RunTimeError(
                node.pos_start,
                node.pos_end,
                f"Unexpected property {_property} for {obj.__class__.__name__}",
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
            if not isinstance(index, Number):
                return res.failure(
                    RunTimeError(
                        node.pos_start,
                        node.pos_end,
                        "Index is expected to be of type Number.",
                    )
                )

            i = int(index.value)
            if i < 0:
                i += len(obj.list_of_elements)
            if i < 0 or i >= len(obj.list_of_elements):
                return res.failure(
                    RunTimeError(
                        node.pos_start, node.pos_end, "Index is out of bounds."
                    )
                )

            element = obj.list_of_elements[i]
            if hasattr(element, 'copy') and isinstance(element, (List, Array)):
                element = element.copy()
            return res.success(
                element.set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        if isinstance(obj, String):
            if not isinstance(index, Number):
                return res.failure(
                    RunTimeError(
                        node.pos_start,
                        node.pos_end,
                        "Index is expected to be of type Number.",
                    )
                )
            i = int(index.value)
            if i < 0:
                i += len(obj.value)
            if i < 0 or i >= len(obj.value):
                return res.failure(
                    RunTimeError(
                        node.pos_start, node.pos_end, "Index is out of bounds."
                    )
                )
            return res.success(
                String(obj.value[i]).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        return res.failure(
            RunTimeError(node.pos_start, node.pos_end, "Given type is not indexable.")
        )

    def visit_SliceNode(self, node, context):
        res = RunTimeResult()
        obj = res.register(self.visit(node.node, context))
        if res.error:
            return res

        if isinstance(obj, (List, Array)):
            length = len(obj.list_of_elements)
            if node.start_node is not None:
                start_val = res.register(self.visit(node.start_node, context))
                if res.error:
                    return res
                if not isinstance(start_val, Number):
                    return res.failure(RunTimeError(node.pos_start, node.pos_end, "Slice start must be a Number."))
                start = int(start_val.value)
            else:
                start = 0

            if node.end_node is not None:
                end_val = res.register(self.visit(node.end_node, context))
                if res.error:
                    return res
                if not isinstance(end_val, Number):
                    return res.failure(RunTimeError(node.pos_start, node.pos_end, "Slice end must be a Number."))
                end = int(end_val.value)
            else:
                end = length

            sliced = obj.list_of_elements[start:end]
            return res.success(
                List(sliced).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        if isinstance(obj, String):
            length = len(obj.value)
            if node.start_node is not None:
                start_val = res.register(self.visit(node.start_node, context))
                if res.error:
                    return res
                if not isinstance(start_val, Number):
                    return res.failure(RunTimeError(node.pos_start, node.pos_end, "Slice start must be a Number."))
                start = int(start_val.value)
            else:
                start = 0

            if node.end_node is not None:
                end_val = res.register(self.visit(node.end_node, context))
                if res.error:
                    return res
                if not isinstance(end_val, Number):
                    return res.failure(RunTimeError(node.pos_start, node.pos_end, "Slice end must be a Number."))
                end = int(end_val.value)
            else:
                end = length

            return res.success(
                String(obj.value[start:end]).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        return res.failure(
            RunTimeError(node.pos_start, node.pos_end, "Cannot slice this type.")
        )

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

        if isinstance(obj, (List, Array)):
            if method_name == "push":
                return self._list_push(obj, args, node, context)
            elif method_name == "drop":
                return self._list_drop(obj, args, node, context)
            elif method_name == "delete":
                return self._list_delete(obj, args, node, context)

        return res.failure(
            RunTimeError(
                node.pos_start,
                node.pos_end,
                f"'{method_name}' is not a method of {obj.__class__.__name__}",
            )
        )

    def _list_push(self, obj, args, node, context):
        res = RunTimeResult()
        if len(args) < 1 or len(args) > 2:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'push' expects 1 or 2 arguments (element, [index]), got {len(args)}.",
                )
            )
        element = args[0]
        index = int(args[1].value) if len(args) == 2 else None
        if index is not None:
            if not isinstance(args[1], Number):
                return res.failure(
                    RunTimeError(node.pos_start, node.pos_end, "Index must be a Number.")
                )
            if index < 0 or index > len(obj.list_of_elements):
                return res.failure(
                    RunTimeError(node.pos_start, node.pos_end, "Index out of bounds.")
                )

        if isinstance(obj, Array):
            err = obj._validate_element(element)
            if err:
                return res.failure(err)

        new_elements = obj.list_of_elements.copy()
        if index is None:
            new_elements.append(element)
        else:
            new_elements.insert(index, element)

        if isinstance(obj, Array):
            result = obj._new_array(new_elements)
        else:
            result = List(new_elements)

        return res.success(result.set_context(context).set_pos(node.pos_start, node.pos_end))

    def _list_drop(self, obj, args, node, context):
        res = RunTimeResult()
        if len(args) != 1:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'drop' expects 1 argument (index), got {len(args)}.",
                )
            )
        if not isinstance(args[0], Number):
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "Index must be a Number.")
            )
        index = int(args[0].value)
        if index < 0 or index >= len(obj.list_of_elements):
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "Index out of bounds.")
            )

        new_elements = obj.list_of_elements.copy()
        del new_elements[index]

        if isinstance(obj, Array):
            result = obj._new_array(new_elements)
        else:
            result = List(new_elements)

        return res.success(result.set_context(context).set_pos(node.pos_start, node.pos_end))

    def _list_delete(self, obj, args, node, context):
        res = RunTimeResult()
        if len(args) != 2:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    f"'delete' expects 2 arguments (first, last), got {len(args)}.",
                )
            )
        if not isinstance(args[0], Number) or not isinstance(args[1], Number):
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "Both indices must be Numbers.")
            )
        start = int(args[0].value)
        end = int(args[1].value)
        if start < 0 or end > len(obj.list_of_elements) or start > end:
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "Invalid range for delete.")
            )

        new_elements = obj.list_of_elements.copy()
        del new_elements[start:end]

        if isinstance(obj, Array):
            result = obj._new_array(new_elements)
        else:
            result = List(new_elements)

        return res.success(result.set_context(context).set_pos(node.pos_start, node.pos_end))
