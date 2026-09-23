# Error Code Format: [CATEGORY][NUMBER]
# Categories:
#   LEX - Lexer Errors
#   SYN - Syntax Errors (Parser)
#   RUN - Runtime Errors
#   ASN - Assignment Errors
#   MOD - Modification Errors
#   CMP - Comparison Errors
#   IMP - Import Errors
#   MTH - Math Errors
#   SHD - Shadowing Errors
#   WRN - Warnings

ERROR_CATALOG = {
    # ==================== LEXER ERRORS ====================
    "LEX001": {
        "name": "Illegal Character",
        "message": "Character '{char}' is not allowed in B#",
        "hint": "Remove the unsupported character or replace it with a valid B# operator/identifier",
    },
    "LEX002": {
        "name": "Double Floating Assigned Error.",
        "message": "A number literal cannot contain more than one decimal point",
        "hint": "Use only one decimal point in number literals (e.g., 3.14, not 3.1.4)",
    },
    # ==================== SYNTAX ERRORS ====================
    # Not Equal Operator
    "SYN001": {
        "name": "Syntax Error",
        "message": "Expected an equalizer after NOT logical operation",
        "hint": "Use '!=' instead of '!' followed by '='",
    },
    # String Errors
    "SYN002": {
        "name": "Syntax Error",
        "message": "Invalid escape sequence '\\{char}'",
        "hint": "Valid escape sequences are: \\n (newline), \\t (tab), \\\\ (backslash), \\' (quote)",
    },
    "SYN003": {
        "name": "Syntax Error",
        "message": "Unterminated string literal, expected closing {quote_char}",
        "hint": "Add the closing quote character to complete the string",
    },
    # Comment Errors
    "SYN004": {
        "name": "Syntax Error",
        "message": "Unterminated block comment. Expected closing '*/'",
        "hint": "Add '*/' to close the block comment",
    },
    # Operator Errors
    "SYN005": {
        "name": "Syntax Error",
        "message": "The '**' operator is not defined",
        "hint": "Use '^' for exponentiation instead of '**'",
    },
    # Parenthesis Errors
    "SYN006": {
        "name": "Syntax Error",
        "message": "Expected ')'",
        "hint": "Add a closing parenthesis to complete the expression",
    },
    "SYN007": {
        "name": "Syntax Error",
        "message": "Expected int, float, identifier, '+', '-', '(', or keyword",
        "hint": "Check the syntax at the indicated position",
    },
    # Import Errors
    "SYN008": {
        "name": "Syntax Error",
        "message": "Expected 'using' keyword to import a module",
        "hint": "Use 'using \"filename\"' to import a module",
    },
    "SYN009": {
        "name": "Syntax Error",
        "message": "Module import name is expected to be a valid string file path",
        "hint": 'The import path must be a string: using "path/to/file"',
    },
    # If/Elif/Else Errors
    "SYN010": {
        "name": "Syntax Error",
        "message": "Expected 'if'",
        "hint": "Use 'if condition then' or 'if condition {{' to start an if statement",
    },
    "SYN011": {
        "name": "Syntax Error",
        "message": "Expected 'then' or '{{' after if condition",
        "hint": "Use 'if condition then' or 'if condition {{' syntax",
    },
    "SYN012": {
        "name": "Syntax Error",
        "message": "Expected 'then' or '{{' after elif condition",
        "hint": "Use 'elif condition then' or 'elif condition {{' syntax",
    },
    # Array Errors
    "SYN013": {
        "name": "Syntax Error",
        "message": "Expected ']' after type in array declaration",
        "hint": "Close the array type declaration with ']'",
    },
    "SYN014": {
        "name": "Syntax Error",
        "message": "Array of List is not supported. Use List for untyped collections.",
        "hint": "Use 'List' instead of 'Array[]' for untyped collections",
    },
    # Variable Declaration Errors
    "SYN015": {
        "name": "Syntax Error",
        "message": "Expected variable identifier name after 'var' or 'const'",
        "hint": "Use 'var name' or 'const name' to declare a variable",
    },
    "SYN016": {
        "name": "Syntax Error",
        "message": "Expected identifier name after ','",
        "hint": "Add a variable name after the comma in multi-variable declaration",
    },
    "SYN017": {
        "name": "Syntax Error",
        "message": "Expected type identifier after ':'",
        "hint": "Specify the variable type after the colon (e.g., 'var x: Number')",
    },
    "SYN018": {
        "name": "Syntax Error",
        "message": "Unknown data type '{type_name}'",
        "hint": "Valid types are: Bool, Number, String, Empty, List, Inf, NaN, Function, Number[], String[], Boolean[], Empty[]",
    },
    "SYN019": {
        "name": "Syntax Error",
        "message": "Multiple initializers in assignment are not supported",
        "hint": "Use a single initializer: 'var x = value'",
    },
    "SYN020": {
        "name": "Syntax Error",
        "message": "Uninitialized 'const' declaration requires a value or type",
        "hint": "Provide a value or type: 'const x = value' or 'const x: Type'",
    },
    # List Errors
    "SYN021": {
        "name": "Syntax Error",
        "message": "Expected '[' for creating a list",
        "hint": "Start a list with '[' and end with ']'",
    },
    "SYN022": {
        "name": "Syntax Error",
        "message": "Expected a valid node inside list",
        "hint": "Check the syntax of the list element",
    },
    "SYN023": {
        "name": "Syntax Error",
        "message": "Expected ',' or ']' for a list definition",
        "hint": "Separate elements with ',' or close the list with ']'",
    },
    # Try/Catch Errors
    "SYN024": {
        "name": "Syntax Error",
        "message": "Expected '{{' after 'try'",
        "hint": "Start the try block with '{{'",
    },
    "SYN025": {
        "name": "Syntax Error",
        "message": "Empty 'try' block is not allowed",
        "hint": "Add at least one statement inside the try block",
    },
    "SYN026": {
        "name": "Syntax Error",
        "message": "Expected '}}' at end of 'try' block",
        "hint": "Close the try block with '}}'",
    },
    "SYN027": {
        "name": "Syntax Error",
        "message": "Expected '(' after 'catch'",
        "hint": "Use 'catch(ErrorType varName)' syntax",
    },
    "SYN028": {
        "name": "Syntax Error",
        "message": "Expected error type name after 'catch('",
        "hint": "Specify the error type: catch(Error e)",
    },
    "SYN029": {
        "name": "Syntax Error",
        "message": "Unknown error type '{error_type}'",
        "hint": "Valid error types are: Error, B_SharpSyntaxError, RunTimeError, AssignmentError, ModificationError, ComparisonError, BSharpMathError, ShadowingError",
    },
    "SYN030": {
        "name": "Syntax Error",
        "message": "Expected ')' after catch clause",
        "hint": "Close the catch parameter list with ')'",
    },
    "SYN031": {
        "name": "Syntax Error",
        "message": "Expected '{{' to start catch block",
        "hint": "Start the catch block with '{{'",
    },
    "SYN032": {
        "name": "Syntax Error",
        "message": "A 'try' block must be followed by at least one 'catch' clause",
        "hint": "Add a catch clause: catch(ErrorType varName)",
    },
    # Nesting/Depth Errors
    "SYN033": {
        "name": "Syntax Error",
        "message": "Expression or block nesting exceeds the maximum depth",
        "hint": "Reduce nesting by extracting sub-expressions or simplifying logic",
    },
    "SYN034": {
        "name": "Syntax Error",
        "message": "Unexpected token or invalid syntax",
        "hint": "Check the syntax at the indicated position",
    },
    # Block Errors
    "SYN035": {
        "name": "Syntax Error",
        "message": "Expected '{{'",
        "hint": "Start a block with '{{'",
    },
    "SYN036": {
        "name": "Syntax Error",
        "message": "Expected '}}'",
        "hint": "Close the block with '}}'",
    },
    # Increment/Decrement Errors
    "SYN037": {
        "name": "Syntax Error",
        "message": "Expected variable identifier after '++' or '--'",
        "hint": "Use 'x++' or '--x' with a variable name",
    },
    "SYN038": {
        "name": "Syntax Error",
        "message": "Invalid increment/decrement expression",
        "hint": "Use 'x++' or '--x' syntax",
    },
    # While Loop Errors
    "SYN039": {
        "name": "Syntax Error",
        "message": "Expected 'while'",
        "hint": "Use 'while condition' to start a while loop",
    },
    "SYN040": {
        "name": "Syntax Error",
        "message": "Expected '{{' or 'then' after while condition",
        "hint": "Use 'while condition then' or 'while condition {{' syntax",
    },
    # Do-While Loop Errors
    "SYN041": {
        "name": "Syntax Error",
        "message": "Expected 'do'",
        "hint": "Use 'do' to start a do-while loop",
    },
    "SYN042": {
        "name": "Syntax Error",
        "message": "Expected '{{' after 'do' statement",
        "hint": "Start the do block with '{{'",
    },
    "SYN043": {
        "name": "Syntax Error",
        "message": "Expected 'while' after 'do' block",
        "hint": "Add 'while condition' after the do block",
    },
    "SYN044": {
        "name": "Syntax Error",
        "message": "Expected '(' after 'while' in do/while",
        "hint": "Wrap the condition in parentheses: while (condition)",
    },
    "SYN045": {
        "name": "Syntax Error",
        "message": "Expected ')' after do/while condition",
        "hint": "Close the condition with ')'",
    },
    # For Loop Errors
    "SYN046": {
        "name": "Syntax Error",
        "message": "Expected 'for'",
        "hint": "Use 'for (init; condition; update)' to start a for loop",
    },
    "SYN047": {
        "name": "Syntax Error",
        "message": "Expected '(' after 'for'",
        "hint": "Wrap the for loop header in parentheses",
    },
    "SYN048": {
        "name": "Syntax Error",
        "message": "Expected ';' after for loop initializer",
        "hint": "Separate for loop parts with ';'",
    },
    "SYN049": {
        "name": "Syntax Error",
        "message": "Expected ';' after for loop condition",
        "hint": "Separate for loop parts with ';'",
    },
    "SYN050": {
        "name": "Syntax Error",
        "message": "Expected ')' after for loop header",
        "hint": "Close the for loop header with ')'",
    },
    "SYN051": {
        "name": "Syntax Error",
        "message": "Expected '{{' or 'then' after for loop expression",
        "hint": "Start the for loop body with '{{' or 'then'",
    },
    # Property Access Errors
    "SYN052": {
        "name": "Syntax Error",
        "message": "Expected property or method name",
        "hint": "Add a property or method name after the '.'",
    },
    # Index/Slice Errors
    "SYN053": {
        "name": "Syntax Error",
        "message": "Expected closing brackets ']'",
        "hint": "Close the index or slice with ']'",
    },
    # Method/Function Call Errors
    "SYN054": {
        "name": "Syntax Error",
        "message": "Expected ')' or ','",
        "hint": "Separate arguments with ',' or close the call with ')'",
    },
    "SYN055": {
        "name": "Syntax Error",
        "message": "Expected ',' or ')'",
        "hint": "Separate arguments with ',' or close the call with ')'",
    },
    # Function Definition Errors
    "SYN056": {
        "name": "Syntax Error",
        "message": "Expected 'fn' or 'function'",
        "hint": "Use 'fn name()' or 'function name()' to define a function",
    },
    "SYN057": {
        "name": "Syntax Error",
        "message": "Unallowed calling of a function by a keyword",
        "hint": "Use a different name that is not a keyword",
    },
    "SYN058": {
        "name": "Syntax Error",
        "message": "Expected function identifier after function name",
        "hint": "Provide a name for the function",
    },
    "SYN059": {
        "name": "Syntax Error",
        "message": "Expected '(' after function name",
        "hint": "Add parentheses for parameters: fn name(params)",
    },
    "SYN060": {
        "name": "Syntax Error",
        "message": "Expected parameter name identifier",
        "hint": "Add a parameter name (e.g., 'fn func(x: Number)')",
    },
    "SYN061": {
        "name": "Syntax Error",
        "message": "Expected type identifier after ':'",
        "hint": "Specify the parameter type (e.g., 'x: Number')",
    },
    "SYN062": {
        "name": "Syntax Error",
        "message": "Duplicate parameter name '{param_name}' in function '{func_name}'",
        "hint": "Use unique parameter names within a function",
    },
    "SYN063": {
        "name": "Syntax Error",
        "message": "Expected ',' or ')' in parameter list",
        "hint": "Separate parameters with ',' or close with ')'",
    },
    "SYN064": {
        "name": "Syntax Error",
        "message": "Unknown return type '{return_type}'",
        "hint": "The type you committed is not a valid type.",
    },
    "SYN065": {
        "name": "Syntax Error",
        "message": "Expected return type identifier after '->'",
        "hint": "Specify the return type: -> ReturnType",
    },
    "SYN066": {
        "name": "Syntax Error",
        "message": "Expected '{{' to start function body block",
        "hint": "Start the function body with '{{'",
    },
    "SYN067": {
        "name": "Syntax Error",
        "message": "Expected 'return'",
        "hint": "Use 'return value' to return from a function",
    },
    "SYN068": {
        "name": "Syntax Error",
        "message": "Expected a caller macro after exclamation.",
        "hint": "Use on of the predefined caller macros.",
    },
    # Struct Errors
    "SYN070": {
        "name": "Syntax Error",
        "message": "Expected 'struct'",
        "hint": "Use 'struct Name { ... }' to define a struct",
    },
    "SYN071": {
        "name": "Syntax Error",
        "message": "Expected struct name identifier",
        "hint": "Provide a name for the struct: struct Name { ... }",
    },
    "SYN072": {
        "name": "Syntax Error",
        "message": "Expected '{{' after struct name",
        "hint": "Start the struct body with '{{'",
    },
    "SYN073": {
        "name": "Syntax Error",
        "message": "Only variable declarations are allowed inside struct",
        "hint": "Structures may not include any non-variable definition code blocks",
    },
    "SYN074": {
        "name": "Syntax Error",
        "message": "Unknown caller macro '{name}'.",
        "hint": "Use one of the predefined caller macros (e.g. 'pragma').",
    },
    "SYN069": {
        "name": "Syntax Error",
        "message": "Caller macros must appear at the top of the file, before any code.",
        "hint": "Move all '!pragma' lines to the file header before any statements",
    },
    # ==================== ENFORCE ERRORS ====================
    "SYN075": {
        "name": "Syntax Error",
        "message": "'!pragma enforce' requires a type annotation for '{var_names}'.",
        "hint": "Declare variables with an explicit type: 'var x : Number = ...'",
    },
    "SYN076": {
        "name": "Syntax Error",
        "message": "'!pragma enforce' requires a type for parameter '{param}' of '{func}'.",
        "hint": "Declare function parameters with an explicit type: '(value : Number)'",
    },
    "SYN077": {
        "name": "Syntax Error",
        "message": "'!pragma enforce' requires function '{func}' to declare a return type.",
        "hint": "Add '-> Type' (use '-> Empty' for procedures that return nothing)",
    },
    # ==================== PRAGMA ARGUMENT ERRORS ====================
    "SYN078": {
        "name": "Syntax Error",
        "message": "Invalid argument for 'precision'. Expected an integer from 0 to 12 or 'default'.",
        "hint": "Usage: '!pragma precision 4' or '!pragma precision default'",
    },
    "SYN079": {
        "name": "Syntax Error",
        "message": "Caller macro '{name}' does not take arguments.",
        "hint": "Remove the argument (e.g. '!pragma enforce')",
    },
    "SYN080": {
        "name": "Syntax Error",
        "message": "Unknown pragma directive '{name}'.",
        "hint": "Known directives: 'enforce', 'precision'",
    },
    # ==================== RUNTIME ERRORS ====================
    # Visitor/Operator Errors
    "RUN001": {
        "name": "RunTime Error",
        "message": "No visitor implemented for node '{node_type}'",
        "hint": "This is an internal error - please report it",
    },
    "RUN002": {
        "name": "RunTime Error",
        "message": "Unknown binary operator '{operator}'",
        "hint": "Check that the operator is supported for the given types",
    },
    "RUN003": {
        "name": "RunTime Error",
        "message": "Unary '-' cannot negate {type_name}",
        "hint": "Only Number, List, and Inf values can be negated",
    },
    "RUN004": {
        "name": "RunTime Error",
        "message": "Unknown unary operator '{operator}'",
        "hint": "Check that the operator is valid",
    },
    # Increment/Decrement Errors
    "RUN005": {
        "name": "RunTime Error",
        "message": "Increment/decrement operations are only supported on Number types",
        "hint": "Use ++ or -- only on Number variables",
    },
    # Function Call Errors
    "RUN006": {
        "name": "RunTime Error",
        "message": "'{name}' is not a function",
        "hint": "Ensure you are calling a defined function",
    },
    "RUN007": {
        "name": "RunTime Error",
        "message": "Maximum call depth exceeded (recursion too deep)",
        "hint": "Reduce recursion depth or use iteration instead",
    },
    "RUN008": {
        "name": "RunTime Error",
        "message": "Cannot use 'return' outside of a function",
        "hint": "Use 'return' only inside function definitions",
    },
    # Property Access Errors
    "RUN009": {
        "name": "RunTime Error",
        "message": "Unexpected property '{property}' for ErrorInstance",
        "hint": "Supported properties: 'name', 'details', 'line', 'file', 'type'",
    },
    "RUN010": {
        "name": "RunTime Error",
        "message": "Unexpected property '{property}' for {type_name}",
        "hint": "Check the available properties for this type",
    },
    "RUN097": {
        "name": "RunTime Error",
        "message": "'{property}' is not a field of struct '{struct_name}'",
        "hint": "Check the struct definition for available fields",
    },
    "RUN098": {
        "name": "RunTime Error",
        "message": "Cannot instantiate '{type_name}' - not a struct",
        "hint": "Only struct types can be instantiated with structName()",
    },
    # Index Access Errors
    "RUN011": {
        "name": "RunTime Error",
        "message": "Index is out of bounds",
        "hint": "Ensure the index is within the valid range for this collection",
    },
    "RUN012": {
        "name": "RunTime Error",
        "message": "Given type is not indexable",
        "hint": "Only List, Array, and String types support indexing",
    },
    # Index Assignment Errors
    "RUN013": {
        "name": "RunTime Error",
        "message": "Cannot assign to string index (strings are immutable)",
        "hint": "Create a new string instead of modifying an existing one",
    },
    "RUN014": {
        "name": "RunTime Error",
        "message": "Target of assignment is not indexable",
        "hint": "Only List, Array, and String types support index assignment",
    },
    # Slice Errors
    "RUN015": {
        "name": "RunTime Error",
        "message": "Cannot slice this type",
        "hint": "Only List, Array, and String types support slicing",
    },
    # Import Errors
    "RUN016": {
        "name": "RunTime Error",
        "message": "Could not import '{file_path}': File not found",
        "hint": "Check that the file exists and the path is correct",
    },
    "RUN017": {
        "name": "RunTime Error",
        "message": "Failed to read module '{file_path}'",
        "hint": "Check file permissions and ensure the file is readable",
    },
    "RUN018": {
        "name": "RunTime Error",
        "message": "Failed to tokenize module '{file_path}'",
        "hint": "Check for syntax errors in the imported module",
    },
    "RUN019": {
        "name": "RunTime Error",
        "message": "Failed to parse module '{file_path}'",
        "hint": "Check for syntax errors in the imported module",
    },
    "RUN020": {
        "name": "RunTime Error",
        "message": "Symbol(s) not found in module '{file_path}'",
        "hint": "Ensure the symbols are exported from the module",
    },
    # Type Errors
    "RUN021": {
        "name": "RunTime Error",
        "message": "{label} must be an integer Number",
        "hint": "Convert the value to an integer before using it as an index",
    },
    # Method Errors
    "RUN022": {
        "name": "RunTime Error",
        "message": "'{method}' is not a method of {type_name}",
        "hint": "Check the available methods for this type",
    },
    "RUN023": {
        "name": "RunTime Error",
        "message": "'{method}' expects {expected} argument(s), got {actual}",
        "hint": "Provide the correct number of arguments",
    },
    # Loop Control Errors
    "RUN024": {
        "name": "RunTime Error",
        "message": "'break' outside loop",
        "hint": "Use 'break' only inside while, for, or do-while loops",
    },
    "RUN025": {
        "name": "RunTime Error",
        "message": "'continue' outside loop",
        "hint": "Use 'continue' only inside while, for, or do-while loops",
    },
    # Module Errors
    "RUN026": {
        "name": "RunTime Error",
        "message": "Module '{file_path}' cannot be found",
        "hint": "Check that the file exists and the path is correct",
    },
    "RUN027": {
        "name": "RunTime Error",
        "message": "Module '{file_path}' exceeds the maximum nesting depth",
        "hint": "Reduce the number of nested imports",
    },
    # Function Return Errors
    "RUN028": {
        "name": "RunTime Error",
        "message": "Function '{func_name}' promises return type '{return_type}' but not all code paths return a value",
        "hint": "Ensure every branch in the function ends with 'return <value>'",
    },
    # ==================== TYPE-SPECIFIC RUNTIME ERRORS ====================
    # Division by Zero
    "RUN099": {
        "name": "RunTime Error",
        "message": "Unexpected type for {type_name} {op} operation.",
        "hint": "Check that the operation is supported for the given type",
    },
    "RUN100": {
        "name": "RunTime Error",
        "message": "Unallowed division by zero",
        "hint": "Ensure the divisor is not zero before dividing",
    },
    "RUN101": {
        "name": "RunTime Error",
        "message": "'%' integer division requires integer operands",
        "hint": "Convert operands to whole numbers before using '%' (integer division)",
    },
    "RUN102": {
        "name": "RunTime Error",
        "message": "Unexpected type for non-number types in modulo operation",
        "hint": "Ensure both operands are Numbers for '~' (modulo) operations",
    },
    "RUN103": {
        "name": "RunTime Error",
        "message": "'~' modulo requires integer operands",
        "hint": "Convert operands to whole numbers before using '~' (modulo)",
    },
    "RUN104": {
        "name": "RunTime Error",
        "message": "Unallowed modulo by zero",
        "hint": "Ensure the divisor is not zero before '~' (modulo) operation",
    },
    "RUN105": {
        "name": "RunTime Error",
        "message": "Unallowed division by zero in exponentiation",
        "hint": "Cannot compute 0 raised to a negative power",
    },
    # Complex Numbers
    "RUN106": {
        "name": "RunTime Error",
        "message": "Complex numbers are not yet supported",
        "hint": "Avoid operations that would result in complex numbers",
    },
    # String Multiplication
    "RUN107": {
        "name": "RunTime Error",
        "message": "String multiplication requires a non-negative integer power factor",
        "hint": "Use a positive integer for string repetition",
    },
    "RUN108": {
        "name": "RunTime Error",
        "message": "String multiplication requires an integer factor",
        "hint": "Convert the multiplier to an integer",
    },
    # List/Array Errors
    "RUN109": {
        "name": "RunTime Error",
        "message": "Insert index {index} is out of bounds for length {length}",
        "hint": "Ensure the index is between 0 and the collection length",
    },
    "RUN110": {
        "name": "RunTime Error",
        "message": "Index {index} is out of bounds for length {length}",
        "hint": "Ensure the index is within the valid range",
    },
    "RUN111": {
        "name": "RunTime Error",
        "message": "List multiplication requires both lists to be the same size",
        "hint": "Use lists of equal length for element-wise multiplication",
    },
    "RUN112": {
        "name": "RunTime Error",
        "message": "Unsupported type '{type_name}' for list multiplication",
        "hint": "Only Number and List types can be multiplied with lists",
    },
    "RUN113": {
        "name": "RunTime Error",
        "message": "Division between two lists is not supported",
        "hint": "Use scalar division instead",
    },
    "RUN114": {
        "name": "RunTime Error",
        "message": "Unsupported type '{type_name}' for list division",
        "hint": "Only Number type can divide a list",
    },
    # Array Validation Errors
    "RUN115": {
        "name": "RunTime Error",
        "message": "Expected {expected_type} element, got Empty (none)",
        "hint": "Use Empty[] for none values in typed arrays",
    },
    "RUN116": {
        "name": "RunTime Error",
        "message": "Expected {expected_type} element, got Empty inside nested list",
        "hint": "Ensure all elements match the array type",
    },
    "RUN117": {
        "name": "RunTime Error",
        "message": "Expected {expected_type} element, got {actual_type} inside nested list",
        "hint": "Ensure all nested elements match the array type",
    },
    "RUN118": {
        "name": "RunTime Error",
        "message": "Expected {expected_type} element, got {actual_type}",
        "hint": "Ensure the element type matches the array declaration",
    },
    "RUN119": {
        "name": "RunTime Error",
        "message": "Unsupported type '{type_name}' for array multiplication",
        "hint": "Only Number type can multiply with arrays",
    },
    "RUN120": {
        "name": "RunTime Error",
        "message": "Division between two arrays or lists is not supported",
        "hint": "Use scalar division instead",
    },
    "RUN121": {
        "name": "RunTime Error",
        "message": "Unsupported type '{type_name}' for array division",
        "hint": "Only Number type can divide an array",
    },
    # Function Execution Errors
    "RUN122": {
        "name": "RunTime Error",
        "message": "Function '{func_name}' expects {expected} arguments, but got {actual}",
        "hint": "Provide the correct number of arguments",
    },
    "RUN123": {
        "name": "RunTime Error",
        "message": "Function '{func_name}' returned type {actual_type}, expected {expected_type}",
        "hint": "Ensure the function returns the declared type",
    },
    # Builtin Function Errors
    "RUN130": {
        "name": "RunTime Error",
        "message": "{function_name}: {error_details}",
        "hint": "Check the builtin function documentation for usage",
    },
    "RUN131": {
        "name": "RunTime Error",
        "message": "'format' expects at least 1 argument (template string)",
        "hint": "Usage: format(template, ...args)",
    },
    "RUN132": {
        "name": "RunTime Error",
        "message": "First argument to 'format' must be a String",
        "hint": "The template string must be the first argument",
    },
    "RUN133": {
        "name": "RunTime Error",
        "message": "read failed: {error_details}",
        "hint": "Check that input is available",
    },
    "RUN134": {
        "name": "RunTime Error",
        "message": "readln failed: {error_details}",
        "hint": "Check that input is available",
    },
    "RUN135": {
        "name": "RunTime Error",
        "message": "'{function_name}' expects 1 argument",
        "hint": "Provide exactly one argument",
    },
    "RUN136": {
        "name": "RunTime Error",
        "message": "Cannot convert '{value}' to a number",
        "hint": "Ensure the string represents a valid number",
    },
    "RUN137": {
        "name": "RunTime Error",
        "message": "Cannot convert {type_name} to Number",
        "hint": "Only String and Number types can be converted to Number",
    },
    "RUN138": {
        "name": "RunTime Error",
        "message": "'time' function requires no arguments",
        "hint": "Call time() without arguments",
    },
    # ==================== ASSIGNMENT ERRORS ====================
    "ASN001": {
        "name": "Uncaught Assignment Error",
        "message": "Attempting to redefine '{name}' which was already defined",
        "hint": "Use a different variable name or remove the existing definition",
    },
    "ASN002": {
        "name": "Uncaught Assignment Error",
        "message": "Attempting to access an unassigned variable '{name}'",
        "hint": "Declare the variable with 'var' before using it",
    },
    "ASN003": {
        "name": "Uncaught Assignment Error",
        "message": "'{name}' is not defined",
        "hint": "Declare the variable with 'var' before using it",
    },
    "ASN004": {
        "name": "Uncaught Assignment Error",
        "message": "Cannot assign value of type {actual_type} to a variable declared with Empty",
        "hint": "Use a compatible type or change the variable declaration",
    },
    "ASN005": {
        "name": "Uncaught Assignment Error",
        "message": "Cannot assign value of type {actual_type} to a variable declared with {expected_type}",
        "hint": "Ensure the value type matches the variable declaration",
    },
    # ==================== MODIFICATION ERRORS ====================
    "MOD001": {
        "name": "Uncaught Modification Error",
        "message": "Cannot mutate a const list/array (it is immutable)",
        "hint": "Use 'var' instead of 'const' for mutable collections",
    },
    "MOD002": {
        "name": "Uncaught Modification Error",
        "message": "Cannot change value of '{name}' of type const",
        "hint": "Use 'var' instead of 'const' if you need to reassign this variable",
    },
    "MOD003": {
        "name": "Uncaught Modification Error",
        "message": "Cannot modify struct type '{name}' – struct types are immutable",
        "hint": "Create an instance via 'var a = Type()' and modify its fields",
    },
    "MOD004": {
        "name": "Uncaught Modification Error",
        "message": "Cannot assign to field '{property}' of temporary struct instance",
        "hint": "Assign via variable: 'var a = Type(); a.field = value'",
    },
    # ==================== COMPARISON ERRORS ====================
    "CMP001": {
        "name": "Comparison Syntax Error",
        "message": "Chained comparisons are not supported",
        "hint": "Combine separate comparisons with 'and' or 'or' (e.g., 'a < b and b < c')",
    },
    "CMP002": {
        "name": "Comparison Syntax Error",
        "message": "Unexpected type for 'and' operation",
        "hint": "Both operands must be Boolean types",
    },
    "CMP003": {
        "name": "Comparison Syntax Error",
        "message": "Unexpected type for 'or' operation",
        "hint": "Both operands must be Boolean types",
    },
    # ==================== IMPORT ERRORS ====================
    "IMP001": {
        "name": "Circular Import Error",
        "message": "Circular import detected: '{file_path}' is already being loaded",
        "hint": "Remove the circular dependency between the imported files",
    },
    # ==================== MATH ERRORS ====================
    "MTH001": {
        "name": "Unexpected Mathematical Error",
        "message": "Result too large to represent",
        "hint": "Use smaller numbers or exponents to avoid overflow",
    },
    # ==================== SHADOWING ERRORS ====================
    "SHD001": {
        "name": "Shadowing Error",
        "message": "Parameter name '{param_name}' shadows the function name '{func_name}'",
        "hint": "Use a different parameter name to avoid shadowing the function name",
    },
    # ==================== WARNINGS ====================
    "WRN001": {
        "name": "Unreachable Code",
        "message": "Unreachable code after 'return' in function '{func_name}'",
        "hint": "Remove or guard the unreachable code after 'return'",
    },
    "WRN002": {
        "name": "Precision Loss",
        "message": "Huge power {base}^{exponent} approximated as float; precision may be lost",
        "hint": "Consider using smaller exponents or a big-integer library",
    },
}


def get_error_info(error_code):
    """
    Retrieve error information for a given error code.

    Args:
        error_code: The error code (e.g., "SYN001", "RUN100")

    Returns:
        dict with 'name', 'message', and 'hint' keys, or None if not found
    """
    return ERROR_CATALOG.get(error_code)


def format_error_message(error_code, **context):
    """
    Format an error message with the given context.

    Args:
        error_code: The error code (e.g., "SYN001")
        **context: Variables to substitute in the message template

    Returns:
        Formatted error message string, or the raw template if formatting fails
    """
    error_info = ERROR_CATALOG.get(error_code)
    if error_info is None:
        return f"Unknown error code: {error_code}"

    try:
        return error_info["message"].format(**context)
    except (KeyError, IndexError):
        return error_info["message"]
