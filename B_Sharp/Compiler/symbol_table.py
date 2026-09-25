"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Lexical Symbol Table and Scope Resolver for B-Sharp Compiler.
Tracks variable declarations, lexical scopes, and symbol resolution
for AOT LLVM code generation.
"""

from typing import Any, Dict, Optional
from B_Sharp.Errors.errors import SemanticError


class Symbol:
    """
    Represents a declared identifier in the B# program.
    """

    def __init__(self, name: str, scope_depth: int):
        self.name = name
        self.scope_depth = scope_depth

        # Allocator Pointer to stack memory (ir.AllocaInstr)
        # Set during LLVM IR generation phase
        self.alloca_ptr = None


class SymbolTable:
    """
    Scoping frame for variables lookup. Supports hierarchical
    scoping (enclosing/parent scopes).
    """

    def __init__(
        self,
        parent: Optional["SymbolTable"] = None,
        scope_depth: int = 0,
    ):

        self.symbols = Dict[str, Symbol] = {}
        self.parent: Optional["SymbolTable"] = parent
        self.scope_depth: int = scope_depth

    def define(self, name: str) -> Symbol:
        """
        Declares a symbol in the current scope.
        """

        symbol = Symbol(name, self.scope_depth)
        self.symbols[name] = symbol
        return symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        """
        Looks up a symbol starting from the current scope up to global scope.
        """

        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def is_local(self, name: str) -> bool:
        """
        Checks if a symbol is defined specifically in the immediate
        local scope.
        """

        return name in self.symbols


class SemanticAnalyzer:
    """
    AST Visitor pass that builds lexical scope trees and validates
    variable references before LLVM codegen.
    """

    def __init__(self):
        self.global_scope = SymbolTable(scope_depth=0)
        self.current_scope = self.global_scope

    def enter_scope(self):
        """
        Creates and steps into a new child scope.
        """
        new_scope = SymbolTable(
            parent=self.current_scope, scope_depth=self.current_scope.scope_depth + 1
        )
        self.current_scope = new_scope
        return new_scope

    def exit_scope(self):
        """
        Steps out of the current child scope to the parent scope.
        """
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def analyze(self, node) -> SymbolTable:
        """
        Entry point to analyze the AST root.
        """
        self.visit(node)
        return self.global_scope

    def visit(self, node):
        if node is None:
            return

        node_type = type(node).__name__
        method_name = f"visit_{node_type}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """
        Default visitor for nodes that contain child sub-nodes.
        """

        for attr in (
            "statements",
            "nodes",
            "body",
            "left_node",
            "right_node",
            "node",
            "value",
        ):
            if hasattr(node, attr):
                child = getattr(node, attr)
                if isinstance(child, list):
                    for item in child:
                        self.visit(item)
                elif child is not None:
                    self.visit(child)

    def visit_VarAssignNode(self, node):
        """
        Handles variable definitions/assignments.
        """
        var_name = getattr(node.var_name_tok, "value", str(node.var_name_tok))

        if hasattr(node, "value_node") and node.value_node:
            self.visit(node.value_node)

        symbol = self.current_scope.lookup(var_name)
        if not symbol:
            self.current_scope.define(var_name)

    def visit_VarAccessNode(self, node):
        """
        Validates variable access references.
        """
        var_name = getattr(node.var_name_tok, "value", str(node.var_name_tok))
        symbol = self.current_scope.lookup(var_name)

        if symbol is None:

            raise SemanticError(
                f"Semantic Error: Identifier '{var_name}' accessed before declaration.",
                node,
            )

    def visit_IfNode(self, node):
        """
        Analyzes conditional branches inside isolated child scopes.
        """
        if hasattr(node, "cases"):
            for condition, body in node.cases:
                self.visit(condition)
                self.enter_scope()
                self.visit(body)
                self.exit_scope()

        if hasattr(node, "else_case") and node.else_case:
            self.enter_scope()
            self.visit(node.else_case)
            self.exit_scope()

    def visit_ForNode(self, node):
        """
        Analyzes loop initialization, condition, increment, and body.
        """
        self.enter_scope()
        if hasattr(node, "var_name_tok"):
            var_name = getattr(node.var_name_tok, "value", str(node.var_name_tok))
            self.current_scope.define(var_name)

        for attr in (
            "start_value_node",
            "end_value_node",
            "step_value_node",
            "body_node",
        ):
            if hasattr(node, attr) and getattr(node, attr):
                self.visit(getattr(node, attr))
        self.exit_scope()

    def visit_WhileNode(self, node):
        """
        Analyzes while loop condition and body scope.
        """
        if hasattr(node, "condition_node"):
            self.visit(node.condition_node)
        self.enter_scope()
        if hasattr(node, "body_node"):
            self.visit(node.body_node)
        self.exit_scope()

    def visit_FuncDefNode(self, node):
        """
        Analyzes function definition and creates function body scope.
        """
        func_name = (
            getattr(node.var_name_tok, "value", None)
            if hasattr(node, "var_name_tok")
            else None
        )
        if func_name:
            self.current_scope.define(func_name)

        self.enter_scope()

        if hasattr(node, "arg_name_toks"):
            for arg_tok in node.arg_name_toks:
                arg_name = getattr(arg_tok, "value", str(arg_tok))
                self.current_scope.define(arg_name)

        if hasattr(node, "body_node"):
            self.visit(node.body_node)
        self.exit_scope()
