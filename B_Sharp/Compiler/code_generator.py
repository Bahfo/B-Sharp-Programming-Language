"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Translates AST nodes into LLVM IR instructions and binds operations
to the C Runtime Support Library
"""

from llvmlite import ir
from B_Sharp.tokens import *


class LLVMCodeGenerator:
    def __init__(self, module_name: str = "bsharp_module"):
        self.module = ir.Module(name=module_name)
        self.module.triple = "x86_64-pc-linux-gnu"

        self.type_i32 = ir.IntType(32)
        self.type_i1 = ir.IntType(1)
        self.type_i8_ptr = ir.IntType(8).as_pointer()
        self.type_double = ir.DoubleType()

        self.bs_value_type = ir.LiteralStructType(
            [self.type_i32, self.type_double, self.type_i32]
        )

        self.symbol_env = {}
        self._declare_runtime_functions()

    def _declare_runtime_functions(self):
        """
        Declare C runtime function prototypes in LLVM IR.
        """

        fn_type = ir.FunctionType(self.bs_value_type, [])
        self.rt_make_none = ir.Function(self.module, fn_type, name="bsharp_make_none")

        fn_type = ir.FunctionType(self.bs_value_type, [self.type_i1])
        self.rt_make_bool = ir.Function(self.module, fn_type, name="bsharp_make_bool")

        fn_type = ir.FunctionType(self.bs_value_type, [self.type_double])
        self.rt_make_number = ir.Function(
            self.module, fn_type, name="bsharp_make_number"
        )

        fn_type = ir.FunctionType(self.bs_value_type, [self.type_i8_ptr])
        self.rt_make_string = ir.Function(
            self.module, fn_type, name="bsharp_make_string"
        )

        binary_op_type = ir.FunctionType(
            self.bs_value_type, [self.bs_value_type, self.bs_value_type]
        )
        self.rt_add = ir.Function(self.module, binary_op_type, name="bsharp_add")
        self.rt_sub = ir.Function(self.module, binary_op_type, name="bsharp_sub")
        self.rt_mul = ir.Function(self.module, binary_op_type, name="bsharp_mul")
        self.rt_div = ir.Function(self.module, binary_op_type, name="bsharp_div")

        self.rt_compare_eq = ir.Function(
            self.module, binary_op_type, name="bsharp_compare_eq"
        )
        self.rt_compare_lt = ir.Function(
            self.module, binary_op_type, name="bsharp_compare_lt"
        )
        self.rt_compare_gt = ir.Function(
            self.module, binary_op_type, name="bsharp_compare_gt"
        )

        print_type = ir.FunctionType(ir.VoidType(), [self.bs_value_type, self.type_i1])
        self.rt_print_value = ir.Function(
            self.module, print_type, name="__bsharp_print_value"
        )

    def generate_code(self, ast_root) -> str:
        """
        Main entry point for generating LLVM IR string from AST.
        """

        main_type = ir.FunctionType(self.type_i32, [])
        main_func = ir.Function(self.module, main_type, name="main")
        block = main_func.append_basic_block(name="entry")

        self.builder = ir.IRBuilder(block)

        self.visit(ast_root)

        self.builder.ret(ir.Constant(self.type_i32, 0))
        return str(self.module)

    def visit(self, node):
        if node is None:
            return self.builder.call(self.rt_make_none, [])

        node_type = type(node).__name__
        visitor = getattr(self, f"visit_{node_type}", self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        res = None
        if hasattr(node, "statements"):
            for stmt in node.statements:
                res = self.visit(stmt)
        elif hasattr(node, "element_nodes"):
            for elem in node.element_nodes:
                res = self.visit(elem)
        elif hasattr(node, "node"):
            res = self.visit(node.node)
        return res or self.builder.call(self.rt_make_none, [])

    def visit_NumberNode(self, node):
        val = float(getattr(node.tok, "value", getattr(node, "value", 0.0)))
        return self.builder.call(
            self.rt_make_number, [ir.Constant(self.type_double, val)]
        )

    def visit_StringNode(self, node):
        val = str(getattr(node.tok, "value", getattr(node, "value", "")))
        fmt = f"{val}\0"
        c_str = ir.Constant(
            ir.ArrayType(ir.IntType(8), len(fmt)), bytearray(fmt.encode("utf-8"))
        )
        global_str = ir.GlobalVariable(self.module, c_str.type, name=f".str.{id(node)}")
        global_str.linkage = "private"
        global_str.initializer = c_str
        ptr = self.builder.gep(
            global_str, [ir.Constant(self.type_i32, 0), ir.Constant(self.type_i32, 0)]
        )
        return self.builder.call(self.rt_make_string, [ptr])

    def visit_ListNode(self, node):
        elements = getattr(node, "element_nodes", [])
        arr_val = self.builder.call(
            self.rt_make_array, [ir.Constant(self.type_size_t, max(len(elements), 8))]
        )
        for elem in elements:
            elem_val = self.visit(elem)
            self.builder.call(self.rt_array_push, [arr_val, elem_val])
        return arr_val

    def visit_VarAssignNode(self, node):
        var_name = str(node.var_name_tok.value)
        val_ir = self.visit(node.value_node)

        if var_name not in self.symbol_env:
            ptr = self.builder.alloca(self.bs_value_type, name=var_name)
            self.symbol_env[var_name] = ptr

        self.builder.store(val_ir, self.symbol_env[var_name])
        return val_ir

    def visit_VarAccessNode(self, node):
        var_name = str(node.var_name_tok.value)
        if var_name in self.symbol_env:
            return self.builder.load(self.symbol_env[var_name], name=f"{var_name}_val")
        return self.builder.call(self.rt_make_none, [])

    def visit_IfNode(self, node):
        merge_block = self.current_function.append_basic_block(name="if_merge")

        cases = getattr(node, "cases", [])
        for cond_node, body_node in cases:
            then_block = self.current_function.append_basic_block(name="if_then")
            next_case_block = self.current_function.append_basic_block(name="if_next")

            cond_val = self.visit(cond_node)
            is_truthy = self.builder.call(self.rt_is_truthy, [cond_val])
            self.builder.cbranch(is_truthy, then_block, next_case_block)

            self.builder.position_at_end(then_block)
            self.visit(body_node)
            self.builder.branch(merge_block)

            self.builder.position_at_end(next_case_block)

        if hasattr(node, "else_case") and node.else_case:
            self.visit(node.else_case)

        self.builder.branch(merge_block)
        self.builder.position_at_end(merge_block)
        return self.builder.call(self.rt_make_none, [])

    def visit_WhileNode(self, node):
        cond_block = self.current_function.append_basic_block(name="while_cond")
        body_block = self.current_function.append_basic_block(name="while_body")
        after_block = self.current_function.append_basic_block(name="while_after")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_val = self.visit(node.condition_node)
        is_truthy = self.builder.call(self.rt_is_truthy, [cond_val])
        self.builder.cbranch(is_truthy, body_block, after_block)

        self.builder.position_at_end(body_block)
        self.visit(node.body_node)
        self.builder.branch(cond_block)

        self.builder.position_at_end(after_block)
        return self.builder.call(self.rt_make_none, [])

    def visit_ForNode(self, node):
        var_name = str(node.var_name_tok.value)
        start_val = self.visit(node.start_value_node)

        ptr = self.builder.alloca(self.bs_value_type, name=var_name)
        self.symbol_env[var_name] = ptr
        self.builder.store(start_val, ptr)

        cond_block = self.current_function.append_basic_block(name="for_cond")
        body_block = self.current_function.append_basic_block(name="for_body")
        after_block = self.current_function.append_basic_block(name="for_after")

        self.builder.branch(cond_block)
        self.builder.position_at_end(cond_block)

        curr_val = self.builder.load(ptr)
        end_val = self.visit(node.end_value_node)
        is_lt = self.builder.call(self.rt_compare_lt, [curr_val, end_val])
        is_truthy = self.builder.call(self.rt_is_truthy, [is_lt])
        self.builder.cbranch(is_truthy, body_block, after_block)

        self.builder.position_at_end(body_block)
        self.visit(node.body_node)

        step_val = (
            self.visit(node.step_value_node)
            if hasattr(node, "step_value_node") and node.step_value_node
            else self.builder.call(
                self.rt_make_number, [ir.Constant(self.type_double, 1.0)]
            )
        )
        new_val = self.builder.call(self.rt_add, [self.builder.load(ptr), step_val])
        self.builder.store(new_val, ptr)
        self.builder.branch(cond_block)

        self.builder.position_at_end(after_block)
        return self.builder.call(self.rt_make_none, [])

    def visit_FuncDefNode(self, node):
        func_name = str(node.var_name_tok.value)
        arg_toks = getattr(node, "arg_name_toks", [])

        param_types = [self.bs_value_type] * len(arg_toks)
        func_type = ir.FunctionType(self.bs_value_type, param_types)
        llvm_func = ir.Function(self.module, func_type, name=func_name)
        self.function_env[func_name] = llvm_func

        previous_builder = self.builder
        previous_function = self.current_function
        previous_env = self.symbol_env.copy()

        entry = llvm_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry)
        self.current_function = llvm_func

        for idx, arg_tok in enumerate(arg_toks):
            param_name = str(arg_tok.value)
            ptr = self.builder.alloca(self.bs_value_type, name=param_name)
            self.builder.store(llvm_func.args[idx], ptr)
            self.symbol_env[param_name] = ptr

        self.visit(node.body_node)

        self.builder.ret(self.builder.call(self.rt_make_none, []))

        self.builder = previous_builder
        self.current_function = previous_function
        self.symbol_env = previous_env

        return self.builder.call(self.rt_make_none, [])

    def visit_CallNode(self, node):
        func_name = (
            str(node.node_to_call.var_name_tok.value)
            if hasattr(node.node_to_call, "var_name_tok")
            else ""
        )
        args = [self.visit(arg) for arg in getattr(node, "arg_nodes", [])]

        if func_name == "write":
            return self.builder.call(
                self.rt_write,
                [args[0]] if args else [self.builder.call(self.rt_make_none, [])],
            )
        elif func_name == "writeln":
            return self.builder.call(
                self.rt_writeln,
                [args[0]] if args else [self.builder.call(self.rt_make_none, [])],
            )
        elif func_name == "len":
            return self.builder.call(self.rt_len, [args[0]])
        elif func_name == "append":
            return self.builder.call(self.rt_array_push, [args[0], args[1]])

        if func_name in self.function_env:
            return self.builder.call(self.function_env[func_name], args)

        return self.builder.call(self.rt_make_none, [])

    def visit_ReturnNode(self, node):
        ret_val = (
            self.visit(node.node_to_return)
            if hasattr(node, "node_to_return") and node.node_to_return
            else self.builder.call(self.rt_make_none, [])
        )
        self.builder.ret(ret_val)
        return ret_val

    def visit_BinOpNode(self, node):
        l = self.visit(node.left_node)
        r = self.visit(node.right_node)
        op = node.op_tok.type

        if op == TOKEN_PLUS:
            return self.builder.call(self.rt_add, [l, r])
        if op == TOKEN_MINUS:
            return self.builder.call(self.rt_sub, [l, r])
        if op == TOKEN_MUL:
            return self.builder.call(self.rt_mul, [l, r])
        if op == TOKEN_DIV:
            return self.builder.call(self.rt_div, [l, r])
        if op == TOKEN_EE:
            return self.builder.call(self.rt_compare_eq, [l, r])
        if op == TOKEN_LT:
            return self.builder.call(self.rt_compare_lt, [l, r])
        if op == TOKEN_GT:
            return self.builder.call(self.rt_compare_gt, [l, r])
        return self.builder.call(self.rt_make_none, [])

    def visit_IndexNode(self, node):
        left_val = self.visit(node.left_node)
        index_val = self.visit(node.index_node)
        return self.builder.call(self.rt_array_get, [left_val, index_val])

    def visit_IndexAssignNode(self, node):
        target_val = self.visit(node.target_node)
        index_val = self.visit(node.index_node)
        value_val = self.visit(node.value_node)
        return self.builder.call(self.rt_array_set, [target_val, index_val, value_val])

    def visit_LogicalOpNode(self, node):
        op = node.op_tok.type

        if op == "NOT":
            val = self.visit(node.node)
            is_truthy = self.builder.call(self.rt_is_truthy, [val])
            not_bool = self.builder.not_(is_truthy)
            return self.builder.call(self.rt_make_bool, [not_bool])

        left_val = self.visit(node.left_node)
        left_truthy = self.builder.call(self.rt_is_truthy, [left_val])

        rhs_block = self.current_function.append_basic_block(name="log_rhs")
        merge_block = self.current_function.append_basic_block(name="log_merge")

        if op == "AND":
            self.builder.cbranch(left_truthy, rhs_block, merge_block)
        else:
            self.builder.cbranch(left_truthy, merge_block, rhs_block)

        self.builder.position_at_end(rhs_block)
        right_val = self.visit(node.right_node)
        rhs_end_block = self.builder.block
        self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(self.bs_value_type, name="log_res")
        phi.add_incoming(left_val, left_truthy.block)
        phi.add_incoming(right_val, rhs_end_block)
        return phi

    def visit_BreakNode(self, node):
        if hasattr(self, "loop_after_stack") and self.loop_after_stack:
            self.builder.branch(self.loop_after_stack[-1])
        return self.builder.call(self.rt_make_none, [])

    def visit_ContinueNode(self, node):
        if hasattr(self, "loop_cond_stack") and self.loop_cond_stack:
            self.builder.branch(self.loop_cond_stack[-1])
        return self.builder.call(self.rt_make_none, [])
