// (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
// Abstracted B-Sharp object holding all object-types methods.

// The B-Sharp source code itself is protected under the GPLv3
// License. However, the standard library is held under the LGPL
// license. For more info, check LICENSE.md file.

#ifndef BSHARPOBJECT_H
#define BSHARPOBJECT_H

#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>

#include "../Runtime/bsharp_errors.h"
#include "../Runtime/bsharp_number.h"

typedef struct BSharpValue BSharpValue;
/*Context for every B-Sharp value.*/
typedef struct BSharpContext BSharpContext;

typedef enum {
    BSharp_Number,                  // Number
    BSharp_String,                  // String
    BSharp_Bool,                    // Bool
    BSharp_Empty,                   // Empty
    BSharp_NaN,                     // NaN
    BSharp_Inf,                     // Inf
    BSharp_List,                    // List
    BSharp_Array,                   // Array
    BSharp_Tuple,                   // Tuple
    BSharp_ErrorInstance,           // Errors
    BSharp_Function,                // Function Head
    BSharp_StructDef,               // Struct Def
    BSharp_StructInstance,          // Struct Call
} BSharpType;

typedef struct {
    BSharpValue** elements;         // pointer to list elements
    size_t size;                    // size of list
    size_t capacity;                // capacity of list
    bool is_const;                  // whether `const` or `var`
} BSharpList;

typedef struct {
    BSharpList list_data;           // An array is a list of one type
    BSharpType element_type;        // type of elements
    int depth;                      // recursion depth. ex: `Number[][]`
    char* type_name;                // full annotation spelling, or NULL
} BSharpArray;

typedef struct {
    BSharpValue** elements;         // pointer to tuple elements
    size_t size;                    // size of tuple

    /*
    A tuple doesn't contain the identifier `bool is_const` because
    it is fixed to a set of elements from the point it is defined
    at. In addition, a tuple doesn't have a depth as its definition
    itself holds how many levels are inside. For example:
    `var x : Tuple(Tuple(Number), 3: Number)`.
    */
} BSharpTuple;

/*A Base struct holding every B-Sharp defined value. It provides
a shared infastructure of position and context that all instances
can inherit from and use.*/
struct BSharpValue {
    BSharpType type;

    BSharpPosition* pos_start;
    BSharpPosition* pos_end;
    BSharpContext* context;

    union {
        BSharpNumber num;           // Type: `Number`
        bool boolean;               // Type: `Bool`
        char* string;               // Type: `String`
        int inf_sign;               // Type: `Inf`
        BSharpList list;            // Type: `List`
        BSharpArray array;          // Type: `Array`
        BSharpTuple tuple;          // Type: `Tuple`
        BSharp_Error* error_inst;   // Type: `ErrorInstance`
        void* function_ptr;         // Type: `FunctionDef`
        void* struct_data;          // Type: `StructDef` / `StructInstance`
    } as;
};

/* The following functions implemented in `BSharpObject.c` hold
the six basic datatypes of B-Sharp. Which are `Number`, `Bool`,
`String`, `Empty`, `NaN`, and `Inf`. These six data types require
operations that are defined next. In addition to memory allocation
function defined later.*/

/* A centralized allocator to guarantee zero-initialization for
shared based fields. This ensures that every `BSharpValue` starts
with a clean memory state, preventing garbage data from corrputing
the interpreter's position tracking or context pointers. */
BSharpValue* __allocate_base_value(BSharpType type);

/*Create `Number` of type `BSharpValue`*/
BSharpValue* __create_number(BSharpNumber value);

/*Create `Bool` of type `BSharpValue`*/
BSharpValue* __create_boolean(bool value);

/*Create `String` of type `BSharpValue`*/
BSharpValue* __create_string(const char* value);

/*Create `Empty` of type `BSharpValue`*/
BSharpValue* __create_empty(void);

/*Create `NaN` of type `BSharpValue`*/
BSharpValue* __create_nan(void);

/*Create `Inf` of type `BSharpValue`*/
BSharpValue* __create_inf(int sign);

/* Create a Number holding the int64 `value` (convenience). */
BSharpValue* __create_number_i64(int64_t value);

/*Following operations are mimic of `class Value` from Python's
implementation of B-Sharp instances core. Each `BSharpValue`
instance must inherit these. In libbsharpobject, these are defined
as a union.

Error positions come from the OPERAND VALUES (`self->pos_start`,
`self->pos_end`) exactly like the interpreter, because the IR always
positions every successfully produced expression result at its AST
node (mirroring `result.set_pos(node.pos_start, node.pos_end)`).
Successful results are therefore returned with NULL positions - the
generated IR must set them; failed results carry final positions and
must be propagated untouched.*/

ReturnStatement __addition(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __subtraction(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __multiplication(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __division(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __int_division(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __modulo_division(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __power(
    BSharpValue* self,
    BSharpValue* other);

ReturnStatement __is_equal(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __not_equal(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __less_than(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __greater_than(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __less_than_equal(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __greater_than_equal(
    BSharpValue* self,
    BSharpValue* other);

ReturnStatement __and_op(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __or_op(
    BSharpValue* self,
    BSharpValue* other);
ReturnStatement __not_op(BSharpValue* self);

bool __is_truthy(BSharpValue* self);

/* Unary `-` mirroring the interpreter's visit_UnaryOpNode: Inf flips
sign, Number/List/Array go through element-wise multiplication by -1
(keep-on-error), everything else fails RUN003. `pos_start`/`pos_end`
are (op_token.pos_start, node.pos_end) - only RUN003 needs them;
successful results are repositioned by the IR. */
ReturnStatement __negate(
    BSharpValue* operand,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end);

/* Mirrors interpreter._require_int: a Number holding an exact
integer passes (BIG values clamp to INT64_MIN/MAX - always out of
range for real containers); floats / Booleans / non-Numbers fail
RUN021 {label} at the supplied (AST node) position. */
ReturnStatement __require_int(
    BSharpValue* value,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end,
    const char* label,
    int64_t* out);

/*Complex Data types definitions*/

BSharpValue* __create_list(size_t initial_capcity);
BSharpValue* __create_array(
    BSharpType element_type,
    int depth,
    const char* type_name,
    size_t initial_capacity
);
BSharpValue* __create_tuple(BSharpValue** elements, size_t size);

/* Element access mirrors visit_IndexAccessNode: `pos_start`/`pos_end`
are the IndexAccessNode's position (object expression start .. index
expression end) because errors are reported at the NODE position, not
the container value's position. Reads of List/Array/Tuple elements
re-position the stored element in place (exactly like Python's
`element.set_pos(...)`). */
ReturnStatement __get_element(
    BSharpValue* container,
    BSharpValue* index_val,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end
);
/* Mirrors visit_IndexAssignNode's final level (RUN139/RUN021/RUN013/
RUN014 at the IndexAssignNode position; MOD001/RUN110/RUN115-118 at
the container value position). On success `new_val` is repositioned to
the node, matching Python's `value.set_pos(node...)`. */
ReturnStatement __set_element(
    BSharpValue* container,
    BSharpValue* index_val,
    BSharpValue* new_val,
    BSharpPosition* pos_start,
    BSharpPosition* pos_end
);

/*A C-Runtime method to provide a deep copy of mutable structures
during assignments or function calls. Thus, LLVM IR will insert
calls to this copy function whenever a variable is assigned to
another identifier, pushed to a list, or returned from a scope.

Mirrors Python's `Value.copy()` family: scalars are shared, only
List/Array copy recursively (nested collections duplicated, `is_const`
reset to false), Tuple/Function/ErrorInstance/Struct* share. Big
bignum payloads may be shared between copies (ops never mutate
inputs; v1 leaks bignums on purpose).*/
BSharpValue* __copy_element(BSharpValue* self);

/* Python's str(Number): exact integers decimal (or
 * "<value too large>" past 4300 digits), floats in repr style.
 * Caller owns the heap string. */
char* __number_to_str(BSharpNumber n);

typedef ReturnStatement (*BSharpMethodFn)
    (BSharpValue*, BSharpValue**, size_t);

typedef struct {
    char* name;
    BSharpMethodFn function_ptr;
    char** param_names;
    size_t param_count;
} BSharpMethod;

typedef struct BSharpStructDef {
    char* name;
    char** field_names;
    size_t field_count;
    BSharpMethod* methods;
    size_t method_count;
} BSharpStructDef;

typedef struct {
    BSharpStructDef* def;
    char** field_names;
    BSharpValue** field_values;
    size_t field_count;
} BSharpStructInstance;

typedef struct {
    BSharpValue* instance;
    BSharpMethodFn function_ptr;
    size_t param_count;
} BSharpBoundMethod;

/* Struct definition / instantiation / property access (see .c) */
BSharpValue* create_struct_definition(
    const char* name,
    const char** field_names,
    size_t field_count,
    BSharpMethod* methods,
    size_t method_count
);
ReturnStatement bsharp_instantiate_struct(
    BSharpValue* struct_def_val,
    BSharpValue** initial_values,
    size_t val_count
);
ReturnStatement bsharp_get_property(
    BSharpValue* instance,
    const char* property_name
);
ReturnStatement bsharp_set_property(
    BSharpValue* instance,
    const char* property_name,
    BSharpValue* new_value
);
BSharpValue* bsharp_error_to_value(BSharp_Error* error);

#endif //BSHARPOBJECT_H
