/** (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
 * This file is a part of the B-Sharp Programming Language Runtime,
 * providing the low-level C Runtime engine, defining the uniform
 * data layout `BSharpValue`, dynamic operations (addition, dynamic
 * typing, truthiness vertification, and memory handling, in addition
 * to printing functions). 
 * 
 * The library is implemented and open-sourced in hopes that it will
 * be useful for people in future who may want to look at this module.
 * 
 * B-Sharp is a Programming Language that is interpreted and compiled
 * thanks to its strong and dynamic interfaces. The Compiler is 
 * implemented using Ahead Of Time Compilation to give B# specific 
 * advantages given in mind when the language was first designed.
 */

// Written by Bahaa Nofal

#ifndef RUNTIME_H
#define RUNTIME_H

#include <stddef.h>

#include <stdbool.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

typedef enum {
    BS_TYPE_NONE = 0,
    BS_TYPE_BOOL,
    BS_TYPE_NUMBER,
    BS_TYPE_STRING,
    BS_TYPE_ARRAY,
    BS_TYPE_OBJECT,
    BS_TYPE_FUNCTION,
} BSharpType;

typedef struct BSharpValue {
    BSharpType type;
    union {
        bool boolean_val;
        double number_val;
        char* string_val;
        void* ptr_val;
        // ptr_val represents a polymorphic pointer for Arrays,
        // Objects, or Functions.
    } as;
    uint32_t ref_count;
} BSharpValue;

#ifdef __cplusplus
extern "C" {
#endif


BSharpValue bsharp_make_none(void);
BSharpValue bsharp_make_bool(bool val);
BSharpValue bsharp_make_number(double val);
BSharpValue bsharp_make_string(const char* str);

// Handling memory management in C too because the LLVM 
// implementation is very hard by hand to implement. We seem to 
// write it using manual garbage collection.

void bsharp_retain(BSharpValue* val);
void bsharp_release(BSharpValue val);

// Dynamic Type Operators

BSharpValue bsharp_add(BSharpValue a, BSharpValue b);
BSharpValue bsharp_sub(BSharpValue a, BSharpValue b);
BSharpValue bsharp_mul(BSharpValue a, BSharpValue b);
BSharpValue bsharp_div(BSharpValue a, BSharpValue b);

// Logical Operations

bool bsharp_is_truthy(BSharpValue val);
BSharpValue bsharp_compare_eq(BSharpValue a, BSharpValue b);
BSharpValue bsharp_compare_lt(BSharpValue a, BSharpValue b);
BSharpValue bsharp_compare_gt(BSharpValue a, BSharpValue b);

// Builtins

void __bsharp_print_value(BSharpValue val, bool newline);
void __bsharp_panic(const char* message);

#ifdef __cplusplus
}
#endif // CPLUSPLUS

#endif // RUNTIME_H