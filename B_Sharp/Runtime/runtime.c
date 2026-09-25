#include "runtime.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>


static const char* value_to_string_buffer(
    BSharpValue val, 
    char* buffer, 
    size_t buffer_size) 
{
    switch (val.type) {
        case BS_TYPE_STRING:
            return val.as.string_val ? val.as.string_val : "";
        case BS_TYPE_NUMBER:
            snprintf(buffer, buffer_size, "%g", val.as.number_val);
            return buffer;
        case BS_TYPE_BOOL:
            return val.as.boolean_val ? "true" : "false";
        default:
            return "none";
    }
}

BSharpValue bsharp_make_none(void) {
    BSharpValue v = {
        .type = BS_TYPE_NONE,
        .as.number_val = 0.0,
        .ref_count = 0
    };
    return v;
}

BSharpValue bsharp_make_bool(bool val) {
    BSharpValue v = {
        .type = BS_TYPE_BOOL,
        .as.boolean_val = val,
        .ref_count = 0
    };
    return v;
}

BSharpValue bsharp_make_number(double val) {
    BSharpValue v = {
        .type = BS_TYPE_NUMBER,
        .as.number_val = val,
        .ref_count = 0
    };
    return v;
}

BSharpValue bsharp_make_string(const char* str) {
    BSharpValue v;
    v.type = BS_TYPE_STRING;
    v.as.string_val = strdup(str ? str : "");
    v.ref_count = 1;
    return v;
}

BSharpValue bsharp_make_array(size_t initial_cap) {
    BSharpValue v;
    v.type = BS_TYPE_ARRAY;

    BSharpArray* arr = malloc(sizeof(BSharpArray));
    if (!arr) {
        bsharp_panic("Memory allocation failure for array container");
    }

    arr->capacity = (initial_cap > 0) ? initial_cap : 8;
    arr->length = 0;
    arr->items = malloc(sizeof(BSharpValue) * arr->capacity);
    if (!arr->items) {
        free(arr);
        bsharp_panic("Memory allocation failure for array items");
    }

    v.as.array_val = arr;
    v.ref_count = 1;
    return v;
}

void bsharp_retain(BSharpValue* val) {
    if (!val) {
        return;
    }

    if (val->type == BS_TYPE_STRING || val->type == BS_TYPE_ARRAY) {
        val->ref_count++;
    }
}

void bsharp_release(BSharpValue val) {
    if (val.type == BS_TYPE_STRING && val.as.string_val) {
        val.ref_count--;
        if (val.ref_count == 0) {
            free(val.as.string_val);
        }
    } else if (val.type == BS_TYPE_ARRAY && val.as.array_val) {
        val.ref_count--;
        if (val.ref_count == 0) {
            BSharpArray* arr = val.as.array_val;
            for (size_t i = 0; i < arr->length; i++) {
                bsharp_release(arr->items[i]);
            }
            free(arr->items);
            free(arr);
        }
    }
}

BSharpValue bsharp_add(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_number(a.as.number_val + b.as.number_val);
    }

    if (a.type == BS_TYPE_STRING || b.type == BS_TYPE_STRING) {
        char buf_a[64];
        char buf_b[64];

        const char* str_a = value_to_string_buffer(a, buf_a, sizeof(buf_a));
        const char* str_b = value_to_string_buffer(b, buf_b, sizeof(buf_b));

        size_t combined_len = strlen(str_a) + strlen(str_b) + 1;
        char* result_str = malloc(combined_len);
        if (!result_str) {
            bsharp_panic("Memory allocation failure during string concatenation");
        }

        strcpy(result_str, str_a);
        strcat(result_str, str_b);

        BSharpValue result_val = bsharp_make_string(result_str);
        free(result_str);
        return result_val;
    }

    bsharp_panic("Invalid operands for '+' operator");
    return bsharp_make_none();
}

BSharpValue bsharp_sub(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_number(a.as.number_val - b.as.number_val);
    }

    bsharp_panic("Operands for '-' must be numbers");
    return bsharp_make_none();
}

BSharpValue bsharp_mul(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_number(a.as.number_val * b.as.number_val);
    }

    bsharp_panic("Operands for '*' must be numbers");
    return bsharp_make_none();
}

BSharpValue bsharp_div(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        if (b.as.number_val == 0.0) {
            bsharp_panic("Division by zero");
        }
        return bsharp_make_number(a.as.number_val / b.as.number_val);
    }

    bsharp_panic("Operands for '/' must be numbers");
    return bsharp_make_none();
}

bool bsharp_is_truthy(BSharpValue val) {
    switch (val.type) {
        case BS_TYPE_NONE:
            return false;

        case BS_TYPE_BOOL:
            return val.as.boolean_val;

        case BS_TYPE_NUMBER:
            return val.as.number_val != 0.0;

        case BS_TYPE_STRING:
            return (val.as.string_val != NULL) && (strlen(val.as.string_val) > 0);

        default:
            return true;
    }
}

BSharpValue bsharp_compare_eq(BSharpValue a, BSharpValue b) {
    if (a.type != b.type) {
        return bsharp_make_bool(false);
    }

    switch (a.type) {
        case BS_TYPE_NONE:
            return bsharp_make_bool(true);

        case BS_TYPE_BOOL:
            return bsharp_make_bool(a.as.boolean_val == b.as.boolean_val);

        case BS_TYPE_NUMBER:
            return bsharp_make_bool(a.as.number_val == b.as.number_val);

        case BS_TYPE_STRING:
            return bsharp_make_bool(strcmp(a.as.string_val, b.as.string_val) == 0);

        default:
            return bsharp_make_bool(a.as.ptr_val == b.as.ptr_val);
    }
}

BSharpValue bsharp_compare_lt(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_bool(a.as.number_val < b.as.number_val);
    }

    return bsharp_make_bool(false);
}

BSharpValue bsharp_compare_gt(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_bool(a.as.number_val > b.as.number_val);
    }

    return bsharp_make_bool(false);
}

BSharpValue bsharp_array_push(BSharpValue arr, BSharpValue item) {
    if (arr.type != BS_TYPE_ARRAY) {
        bsharp_panic("Target is not an array");
    }

    BSharpArray* array_ptr = arr.as.array_val;

    if (array_ptr->length >= array_ptr->capacity) {
        array_ptr->capacity *= 2;
        BSharpValue* new_items = 
            realloc(array_ptr->items, sizeof(BSharpValue) * array_ptr->capacity);
        if (!new_items) {
            bsharp_panic("Failed to reallocate memory for array expansion");
        }
        array_ptr->items = new_items;
    }

    array_ptr->items[array_ptr->length++] = item;
    bsharp_retain(&item);

    return arr;
}

BSharpValue bsharp_array_get(BSharpValue arr, BSharpValue idx) {
    if (arr.type != BS_TYPE_ARRAY || idx.type != BS_TYPE_NUMBER) {
        bsharp_panic("Invalid array access operands");
    }

    size_t index = (size_t)idx.as.number_val;
    if (index >= arr.as.array_val->length) {
        bsharp_panic("Array index out of bounds");
    }

    return arr.as.array_val->items[index];
}

BSharpValue bsharp_array_set(BSharpValue arr, BSharpValue idx, BSharpValue val) {
    if (arr.type != BS_TYPE_ARRAY || idx.type != BS_TYPE_NUMBER) {
        bsharp_panic("Invalid array assignment operands");
    }

    size_t index = (size_t)idx.as.number_val;
    if (index >= arr.as.array_val->length) {
        bsharp_panic("Array index out of bounds");
    }

    arr.as.array_val->items[index] = val;
    bsharp_retain(&val);

    return val;
}

BSharpValue bsharp_builtin_write(BSharpValue val) {
    switch (val.type) {
        case BS_TYPE_NONE:
            printf("none");
            break;

        case BS_TYPE_BOOL:
            printf("%s", val.as.boolean_val ? "true" : "false");
            break;

        case BS_TYPE_NUMBER:
            printf("%g", val.as.number_val);
            break;

        case BS_TYPE_STRING:
            printf("%s", val.as.string_val);
            break;

        case BS_TYPE_ARRAY:
            printf("<array len=%zu>", val.as.array_val->length);
            break;

        default:
            printf("<object>");
            break;
    }

    fflush(stdout);
    return bsharp_make_none();
}

BSharpValue bsharp_builtin_writeln(BSharpValue val) {
    bsharp_builtin_write(val);
    printf("\n");
    fflush(stdout);
    return bsharp_make_none();
}

BSharpValue bsharp_builtin_len(BSharpValue val) {
    if (val.type == BS_TYPE_STRING) {
        return bsharp_make_number((double)strlen(val.as.string_val));
    }

    if (val.type == BS_TYPE_ARRAY) {
        return bsharp_make_number((double)val.as.array_val->length);
    }

    return bsharp_make_number(0.0);
}

void bsharp_panic(const char* message) {
    fprintf(stderr, "B# Panic: %s\n", message);
    exit(EXIT_FAILURE);
}