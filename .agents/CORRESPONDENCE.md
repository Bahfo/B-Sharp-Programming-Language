# Grammar ↔ Implementation correspondence

Rule numbers refer to `BSharp.grammar` sections. Line numbers are for the
current tree (`B_Sharp/ASTNodes/parser.py` unless noted).

## Program / statements

| Grammar rule | Parser function | AST node(s) | Tests |
|---|---|---|---|
| program | `parser()` :1401 (EOF check → SYN034) | `StatementsNode` (nodes.py:171) | test_programs.py, conformance/ |
| statements / block | `statements()` :1345, `block()` :1422 (depth gate) | `StatementsNode` | test_syntax.py (separators), Tests/ast/ |
| statement dispatch | `statement()` :1212 (keyword → `=` fast path → speculative `call`+`=` → expression) | all below | test_syntax.py |

## Declarations

| Grammar rule | Parser function | AST node(s) | Tests |
|---|---|---|---|
| var_decl | `var_decl()` :848 | `VariableAssignNode` (:55), `MultiVariableAssignNode` (:75) | test_variables.py, test_variables.bsharp |
| type / tuple_params | `_parse_type_after_base()` :724, `_parse_tuple_params()` :749, `_parse_array_suffix()` :823, `_read_slot_type()` :734 | token spelling (no node) | test_llvm_types.py, test_tuples.py |
| fn_def / param | `fn_def()` :1988, `_param_default()` :1923 | `FunctionDefNode` (:274) | test_functions.bsharp, test_named_arguments.py |
| return_stmt | `return_statement()` :2284 | `ReturnNode` (:311) | test_syntax.py, test_functions.bsharp |
| increment_stmt | `increment_or_decrement()` :1472 | `IncrementNode` (:220) | test_syntax.py (prefix/postfix) |
| struct_def | `struct_def()` :2340 | `StructDefNode` (:446) | test_structures_comprehensive.py |
| container_def | `container_def()` :2488 | `ContainerDefNode` (nodes.py:469) | test_containers.py |
| self_stmt | `self_statement()` :2424; `self` atom in `_atom()` | `SelfNode` (:516), `SelfAccessNode` (:528), `SelfAssignNode` (:541) | test_containers.py |

## Expressions

| Grammar rule | Parser function | AST node(s) | Tests |
|---|---|---|---|
| expression…is_expr | `expression()` :696, `or_expression()` :690, `and_expression()` :687, `is_expression()` :693, `binary_operation()` :699 | `BinaryOpNode` (:43) | test_syntax.py (precedence), test_comparisons.py |
| comparison (single) | `comparison()` :662 (2nd op → CMP001) | `BinaryOpNode` | test_comparisons.py |
| term / factor | `term()` :659, `factor()` :654 | `BinaryOpNode` | test_syntax.py |
| unary / power | `_unary()` :625, `power()` :602 (right-assoc `^`) | `UnaryOpNode` (:32), `BinaryOpNode` | test_syntax.py |
| call/postfix | `call()` :1706 | below | Tests/ast/ |
| call_suffix | `finish_call()` :1939 | `CallNode` (:288) | test_named_arguments.py |
| argument (named) | `_call_argument()` :1899 | `CallNode.arg_names` | test_named_arguments.py |
| index_suffix | `parse_index_or_slice()` :1794 | `IndexAccessNode` (:329), `SliceNode` (:337) | test_lists_arrays.bsharp, test_tuples.py |
| dot_suffix | `call()` DOT branch :1723, `finish_method_call()` :1853 | `PropertyAccessNode` (:321), `MethodCallNode` (:354) | test_lists_arrays.bsharp |
| dcolon_suffix | `call()` DCOLON branch (~:1753) | `ContainerAccessNode` (:486) | test_containers.py |
| atom literals | `_atom()` :~136–270 | `NumberNode` (:6), `StringNode` (:185), `CharNode` (:195), `BooleanNode` (:22), `NoneNode` (:119), `NaNNode` (:379), `InfinityNode` (:385) | test_datatypes.bsharp, test_llvm_types.py |
| cast | `_cast_expression()` :338 | `CastNode` (:207) | test_llvm_types.py |
| tuple/grouping | `_atom()` paren branch | `TupleNode` (:144) | test_tuples.py |
| list literal | `make_list()` :969 | `ListNode` (:132) | test_lists_arrays.bsharp |
| if as expression | `if_expression()` :507 | `IfNode` (:156) | test_syntax.py, test_control_flow.bsharp |
| assignable writes | `statement()` speculative branch :~1290 | `IndexAssignNode` (:346), `PropertyAssignNode` (:457), `ContainerAssignNode` (:502), `VariableReassignNode` (:96) | test_variables.py, test_containers.py |

## Control flow / misc

| Grammar rule | Parser function | AST node(s) | Tests |
|---|---|---|---|
| if_expr | `if_expression()` :507 | `IfNode` | test_syntax.py, test_control_flow.bsharp |
| while_stmt | `while_expression()` :1503 | `WhileNode` (:237) | test_syntax.py, test_control_flow.bsharp |
| do_stmt | `do_expression()` :1542 | `DoNode` (:249) | test_do.bsharp |
| for_stmt | `for_expression()` :1611 | `ForNode` (:260) | test_syntax.py, test_control_flow.bsharp |
| using_stmt | `import_module()` :432, `resolve_import_path()` :484 | `ImportNode` (:368) | test_imports.bsharp, test_module_timing.py |
| jump_stmt | `statement()` :1212–1245 | `BreakNode` (:391), `ContinueNode` (:400), `PassNode` (:409) | test_control_flow.bsharp |
| try_stmt | `try_statement()` :1036 | `TryCatchNode` (:434), `CatchNode` (:418) | test_try_catch_comprehensive.py |
| preproc_ifver | `_check_version()` :281 | none (inclusion) / empty block | test_pragmas.py, StdLib ifver use |

## Lexer / frontend

| Grammar rule | Implementation | Tests |
|---|---|---|
| All token rules | `Lexer.tokenize()` (lexer.py:371), `numberize()` :57, `identifiers()` :156, `stringnize()` :260, `charnize()` :303, `commentize()` :350, `Token` (lexer.py:12) | test_llvm_types.py (literals), test_syntax.py (strings) |
| Caller macros | `make_token_not_equal()` :177, `check_pragma()` :187 (`!` handling) | test_pragmas.py |
| Preproc `[#…]` | `check_predefined_macros()` :209, `[` branch :508 | test_pragmas.py |
| Pragma pre-pass | `preprocess_pragmas()` (caller_macros.py:68), `parse_source()` (frontend.py:24) | test_pragmas.py, test_module_timing.py |
| Keyword/type tables | `tokens.py:85–153` (KEYWORDS, TYPE_KEYWORDS, macros) | test_syntax.py (keyword/type binding tests) |
