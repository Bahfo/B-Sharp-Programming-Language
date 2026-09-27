from B_Sharp.ASTNodes.parser import *
from B_Sharp.ASTNodes.parser import _with_recursion_headroom
from B_Sharp.CodeExecution.caller_macros import (
    get_config,
    round_number,
    round_result,
    render_value,
    preprocess_pragmas,
)
from B_Sharp.ASTNodes.instances import String


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

    def _cfg(self, node):
        """Per-file config for the module a node textually belongs to."""
        if node is None or node.pos_start is None:
            return DEFAULT_CONFIG
        return get_config(node.pos_start.file_name)

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
                "RUN001",
                {"node_type": type(node).__name__},
            )
        )

    ################################################################
    # Visitors
    ################################################################

    def visit_NumberNode(self, node, context):
        value = round_number(node.token.value, self._cfg(node))
        return RunTimeResult().success(
            Number(value).set_context(context).set_pos(node.pos_start, node.pos_end)
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

        node_cfg = self._cfg(node)

        if node.op_token.type == TOKEN_PLUS:
            # Under a precision pragma, string concatenation keeps the
            # per-file rendering of the number operand ("n=" + 3.14159 -> "n=3.14").
            if (
                node_cfg.precision is not None
                and isinstance(left, String)
                and isinstance(right, Number)
            ):
                right = String(render_value(right, node_cfg))
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
                "RUN002",
                {"operator": node.op_token.value or node.op_token.type},
            )

        if error:
            return res.failure(error)
        else:
            result = round_result(result, node_cfg)
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
                    "RUN003",
                    {"type_name": type(operand).__name__},
                )
        elif node.op_token.type == TOKEN_PLUS:
            result, error = operand, None
        elif node.op_token.type == TOKEN_KEYWORD and node.op_token.value == "not":
            result, error = operand.not_()
        else:
            result, error = None, RunTimeError(
                node.op_token.pos_start,
                node.op_token.pos_end,
                "RUN004",
                {"operator": node.op_token.value},
            )

        if error:
            return res.failure(error)
        result = round_result(result, self._cfg(node))
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

        data_type_name = node.data_type.value if node.data_type else None
        data_type_class = resolve_type(data_type_name)

        if is_implicit:
            # Fallback per Docs/1_Common/2_data_types.md:136
            value = default_for_type(
                data_type_class,
                node.pos_start,
                node.pos_end,
                context,
                depth=max(1, array_depth(data_type_name)),
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
            value = data_type_class(
                value.list_of_elements, depth=max(1, array_depth(data_type_name))
            )
            value.type_name = data_type_name
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

        data_type_name = node.data_type.value if node.data_type else None
        data_type_class = resolve_type(data_type_name)

        if is_implicit:
            # Fallback per Docs/1_Common/2_data_types.md:136
            value = default_for_type(
                data_type_class,
                node.names[0].pos_start,
                node.names[0].pos_end,
                context,
                depth=max(1, array_depth(data_type_name)),
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
            value = data_type_class(
                value.list_of_elements, depth=max(1, array_depth(data_type_name))
            )
            value.type_name = data_type_name
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
            current, cur_err = context.variables.get(
                var_name, node.pos_start, node.pos_end
            )
            if cur_err:
                return res.failure(cur_err)
            depth = current.depth if isinstance(current, Array) else 1
            type_name = current.type_name if isinstance(current, Array) else None
            value = declared_type(value.list_of_elements, depth=depth)
            value.type_name = type_name
            value.set_context(context).set_pos(node.pos_start, node.pos_end)
            val_err = value._validate_all()
            if val_err:
                return res.failure(val_err)

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
                    "RUN005",
                )
            )

        old_num = val.value
        node_cfg = self._cfg(node)
        new_num = old_num + 1 if node.op_tok.type == TOKEN_INC else old_num - 1
        new_num = round_number(new_num, node_cfg)
        new_val = (
            Number(new_num).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

        _, assign_err = context.variables.set_pos(node.pos_start, node.pos_end).assign(
            var_name, new_val
        )
        if assign_err:
            return res.failure(assign_err)

        return res.success(
            Number(round_number(old_num if node.is_postfix else new_num, node_cfg))
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

        # F1: if promised return type, body must guarantee a `return <value>` on
        # all paths. `-> Empty` is a procedure: falling off the end is the
        # intended completion, so no explicit return is demanded.
        if func_value.return_type is not None and func_value.return_type is not Empty:

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
                if isinstance(n, TryCatchNode):
                    if not _always_returns(n.try_body):
                        return False
                    for catch in n.catch_nodes:
                        if not _always_returns(catch.body_node):
                            return False
                    return True
                if isinstance(n, DoNode):
                    return False
                return False

            if not _always_returns(body_node):
                return res.failure(
                    B_SharpSyntaxError(
                        node.var_name_tok.pos_start,
                        node.var_name_tok.pos_end,
                        "RUN028",
                        {
                            "func_name": func_name,
                            "return_type": func_value.return_type.__name__,
                        },
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
            if isinstance(n, TryCatchNode):
                if not _always_returns_for_unreachable(n.try_body):
                    return False
                for catch in n.catch_nodes:
                    if not _always_returns_for_unreachable(catch.body_node):
                        return False
                return True
            if isinstance(n, WhileNode):
                return False
            if isinstance(n, ForNode):
                return False
            if isinstance(n, DoNode):
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
                                func_name,
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
                    elif isinstance(s, TryCatchNode):
                        _emit_unreachable(s.try_body)
                        for c in s.catch_nodes:
                            _emit_unreachable(c.body_node)
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

        if not isinstance(value_to_call, (Function, BuiltinFunction, StructDefinition)):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN006",
                    {"name": str(node.node_to_call)},
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

        if isinstance(value_to_call, StructDefinition):
            instance, err = value_to_call.instantiate(
                self, node.pos_start, node.pos_end
            )
            if err:
                return res.failure(err)
            return res.success(
                instance.set_pos(node.pos_start, node.pos_end).set_context(context)
            )

        if self.current_call_depth >= self.max_call_depth:
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN007",
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
                    "RUN008",
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

        # ErrorInstance exposes caught error properties: name, details, line, file, type
        if isinstance(obj, ErrorInstance):
            prop_val = obj.get_property(_property)
            if prop_val is not None:
                return res.success(prop_val.set_context(context).set_pos(*pos))
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN009",
                    {"property": _property},
                )
            )

        # Unified size API: both .length and .size work on every
        # sized builtin type (String, List, Array).
        sized_types = (List, Array, String)
        if isinstance(obj, sized_types) and _property in ("length", "size"):
            size = (
                len(obj.value) if isinstance(obj, String) else len(obj.list_of_elements)
            )
            return res.success(Number(size).set_context(context).set_pos(*pos))

        if isinstance(obj, StructInstance):
            field_val, err = obj.get_field(_property, node.pos_start, node.pos_end)
            if err:
                return res.failure(
                    RunTimeError(
                        node.pos_start,
                        node.pos_end,
                        "RUN097",
                        {"property": _property, "struct_name": obj.struct_name},
                    )
                )
            return res.success(field_val.set_context(context).set_pos(*pos))

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
                "RUN010",
                {"property": _property, "type_name": obj.__class__.__name__},
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
                        node.pos_start,
                        node.pos_end,
                        "RUN011",
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
                        node.pos_start,
                        node.pos_end,
                        "RUN011",
                    )
                )
            return res.success(
                String(obj.value[i])
                .set_context(context)
                .set_pos(node.pos_start, node.pos_end)
            )

        return res.failure(
            RunTimeError(
                node.pos_start,
                node.pos_end,
                "RUN012",
            )
        )

    def visit_IndexAssignNode(self, node, context):
        res = RunTimeResult()
        # target is an IndexAccess chain: root[i1][i2]...[in]
        target = node.target

        index_nodes = []
        cursor = target
        while isinstance(cursor, IndexAccessNode):
            index_nodes.append(cursor.index_node)
            cursor = cursor.node
        index_nodes.reverse()

        if not index_nodes:
            # Defensive: parser only builds index chains for assignment
            return res.failure(
                RunTimeError(node.pos_start, node.pos_end, "RUN014")
            )

        container = res.register(self.visit(cursor, context))
        if res.error:
            return res

        # Walk intermediate levels; missing/none rows auto-vivify
        for idx_node in index_nodes[:-1]:
            idx_val = res.register(self.visit(idx_node, context))
            if res.error:
                return res
            container = res.register(
                self._assign_step(container, idx_val, idx_node, context)
            )
            if res.error:
                return res

        index_val = res.register(self.visit(index_nodes[-1], context))
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
                    "RUN013",
                )
            )

        return res.failure(
            RunTimeError(
                node.pos_start,
                node.pos_end,
                "RUN014",
            )
        )

    def _assign_step(self, container, idx_val, idx_node, context):
        """Resolves one intermediate level of an index-assign chain.

        Missing rows and `none` slots auto-vivify (fresh row objects);
        non-indexable slots fail with RUN013/RUN014. Reads never vivify.
        """
        res = RunTimeResult()

        if isinstance(container, (List, Array)):
            i, err = self._require_int(idx_val, idx_node)
            if err:
                return res.failure(err)
            n = len(container.list_of_elements)
            if i < 0:
                i += n
            if i < 0:
                return res.failure(
                    RunTimeError(idx_node.pos_start, idx_node.pos_end, "RUN011")
                )
            if i >= n:
                return self._vivify_slot(container, i, idx_node, context)
            slot = container.list_of_elements[i]
            if isinstance(slot, (List, Array)):
                return res.success(slot)
            if isinstance(slot, Empty):
                return self._vivify_slot(container, i, idx_node, context)
            if isinstance(slot, String):
                return res.failure(
                    RunTimeError(idx_node.pos_start, idx_node.pos_end, "RUN013")
                )
            return res.failure(
                RunTimeError(idx_node.pos_start, idx_node.pos_end, "RUN014")
            )

        if isinstance(container, String):
            return res.failure(
                RunTimeError(idx_node.pos_start, idx_node.pos_end, "RUN013")
            )
        return res.failure(
            RunTimeError(idx_node.pos_start, idx_node.pos_end, "RUN014")
        )

    def _vivify_slot(self, parent, i, idx_node, context):
        """Grows `parent` at index `i` with a fresh empty row and returns it."""
        res = RunTimeResult()

        if isinstance(parent, Array):
            row = parent.fresh_row()
            if row is None:
                # depth-1 typed array holds scalars: cannot nest into it
                return res.failure(
                    RunTimeError(idx_node.pos_start, idx_node.pos_end, "RUN014")
                )
        else:
            row = List([])
        row.set_pos(idx_node.pos_start, idx_node.pos_end).set_context(context)

        _, err = parent.assign_at(i, row)
        if err:
            return res.failure(err)
        # Re-read: typed assign_at stores an independent copy of the row
        return res.success(parent.list_of_elements[i])

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
            RunTimeError(
                node.pos_start,
                node.pos_end,
                "RUN015",
            )
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
                    "RUN016",
                    {"file_path": file_path},
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
                    "RUN017",
                    {"file_path": file_path},
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
                    "RUN018",
                    {"file_path": file_path},
                )
            )
            return None

        tokens, module_cfg, macro_error = preprocess_pragmas(tokens, file_path)
        if macro_error:
            res.failure(macro_error)
            return None

        module_parser = Parser(tokens, file_config=module_cfg)
        try:
            ast = module_parser.parser()
        except ParseDepthExceeded:
            ast = ParserResults().failure(
                B_SharpSyntaxError(
                    tokens[-1].pos_start,
                    tokens[-1].pos_end,
                    "RUN027",
                    {"file_path": file_path},
                )
            )
        if ast.error:
            res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN019",
                    {"file_path": file_path},
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
                    file_path,
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
                        "RUN020",
                        {"file_path": file_path},
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
                "RUN021",
                {"label": label},
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
                    "RUN022",
                    {"method": method_name, "type_name": obj.__class__.__name__},
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
                    "RUN022",
                    {"method": method_name, "type_name": obj.__class__.__name__},
                )
            )

        lo, hi = arities[method_name]
        if not (lo <= len(args) <= hi):
            expected = str(lo) if lo == hi else f"{lo} to {hi}"
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN023",
                    {"method": method_name, "expected": expected, "actual": len(args)},
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
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN024",
                )
            )
        res.should_break = True
        res.value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        return res

    def visit_ContinueNode(self, node, context):
        res = RunTimeResult()
        if not self._inside_loop(context):
            return res.failure(
                RunTimeError(
                    node.pos_start,
                    node.pos_end,
                    "RUN025",
                )
            )
        res.should_continue = True
        res.value = Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
        return res

    def visit_TryCatchNode(self, node, context):
        res = RunTimeResult()
        res.register(self.visit(node.try_body, context))

        if res.error is None:
            if res.func_return_value is not None:
                return res
            if res.should_break or res.should_continue:
                return res
            return res.success(
                Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        caught_error = res.error
        res.error = None

        for catch_node in node.catch_nodes:
            err_type_name = catch_node.exception.value
            err_type_class = ERROR_TYPE_MAP.get(err_type_name)

            if err_type_class is None:
                continue

            if not isinstance(caught_error, err_type_class):
                continue

            err_var_tok = catch_node.exception_var

            if err_var_tok is not None:
                error_instance = (
                    ErrorInstance(caught_error)
                    .set_pos(err_var_tok.pos_start, err_var_tok.pos_end)
                    .set_context(context)
                )

                catch_context = Context(
                    display_name=f"<catch {err_type_name}>",
                    parent=context,
                    parent_entry_pos=catch_node.pos_start,
                    in_function=context.in_function,
                    in_loop=context.in_loop,
                )

                _, define_err = catch_context.variables.set_pos(
                    err_var_tok.pos_start, err_var_tok.pos_end
                ).define(
                    name=err_var_tok.value,
                    data_type=None,
                    value=error_instance,
                    is_const=False,
                )
                if define_err:
                    return res.failure(define_err)

                catch_res = res.register(
                    self.visit(catch_node.body_node, catch_context)
                )
            else:
                catch_res = res.register(self.visit(catch_node.body_node, context))

            if res.error:
                return res
            if res.func_return_value is not None:
                return res
            if res.should_break or res.should_continue:
                return res
            return res.success(
                Empty().set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        return res.failure(caught_error)

    def visit_StructDefNode(self, node, context):
        res = RunTimeResult()
        struct_name = node.name.value
        struct_def = StructDefinition(
            name=struct_name,
            member_nodes=node.member_nodes,
            parent_context=context,
        ).set_pos(node.pos_start, node.pos_end)

        _, error = context.variables.set_pos(node.pos_start, node.pos_end).define(
            name=struct_name,
            data_type=StructDefinition,
            value=struct_def,
            is_const=True,
        )
        if error:
            return res.failure(error)

        return res.success(struct_def)

    def visit_PropertyAssignNode(self, node, context):
        res = RunTimeResult()
        obj = res.register(self.visit(node.target, context))
        if res.error:
            return res

        val = res.register(self.visit(node.value, context))
        if res.error:
            return res

        # --- Struct type immutability: cannot modify struct definition itself ---
        if isinstance(obj, StructDefinition):
            struct_name = getattr(obj, "name", "struct")
            return res.failure(
                ModificationError(
                    node.pos_start,
                    node.pos_end,
                    "MOD003",
                    {"name": struct_name},
                )
            )

        if isinstance(obj, StructInstance):
            if isinstance(node.target, CallNode):
                prop_name = node.property_name.value
                return res.failure(
                    ModificationError(
                        node.pos_start,
                        node.pos_end,
                        "MOD004",
                        {"property": prop_name},
                    )
                )
            prop_name = node.property_name.value
            assigned_val, err = obj.set_field(
                prop_name, val, node.pos_start, node.pos_end
            )
            if err:
                if isinstance(err, AssignmentError) and err.error_code == "ASN002":
                    return res.failure(
                        RunTimeError(
                            node.pos_start,
                            node.pos_end,
                            "RUN097",
                            {"property": prop_name, "struct_name": obj.struct_name},
                        )
                    )
                return res.failure(err)
            return res.success(assigned_val)

        return res.failure(RunTimeError(node.pos_start, node.pos_end, "RUN014"))
