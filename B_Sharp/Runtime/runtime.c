#include "runtime.h"

BSharpValue bsharp_make_none(void) {
    BSharpValue v;
    v.type = BS_TYPE_NONE;
    v.as.number_val = 0.0;
    v.ref_count = 0;
    return v;
}

BSharpValue bsharp_make_bool(bool val) {
    BSharpValue v;
    v.type = BS_TYPE_BOOL;
    v.as.boolean_val = val;
    v.ref_count = 0;
    return v;
}

BSharpValue bsharp_make_number(double val) {
    BSharpValue v;
    v.type = BS_TYPE_NUMBER;
    v.as.number_val = val;
    v.ref_count = 0;
    return v;
}

BSharpValue bsharp_make_string(const char* str) {
    BSharpValue v;
    v.type = BS_TYPE_STRING;
    if (str == NULL) {
        v.as.string_val = strdup("");
    } else {
        v.as.string_val = strdup(str);
    }
    v.ref_count = 1;
    return v;
}

void bsharp_retain(BSharpValue* val) {
    if (val && val->type == BS_TYPE_STRING && val->as.string_val) {
        val->ref_count++;
    }
}

void bsharp_release(BSharpValue val) {
    if (val.type == BS_TYPE_STRING && val.as.string_val) {
        if (val.ref_count <= 1) {
            free(val.as.string_val);
        }
    }
}

BSharpValue bsharp_add(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_number(a.as.number_val + b.as.number_val);
    }

    if (a.type == BS_TYPE_STRING || b.type == BS_TYPE_STRING) {
        char buffer_a[64];
        char buffer_b[64];
        const char* str_a = NULL;
        const char* str_b = NULL;

        if (a.type == BS_TYPE_STRING) {
            str_a = a.as.string_val;
        } else if (a.type == BS_TYPE_NUMBER) {
            snprintf(buffer_a, sizeof(buffer_a), "%g", a.as.number_val);
            str_a = buffer_a;
        } else {
            str_a = (a.type == BS_TYPE_BOOL) 
                ? (a.as.boolean_val ? "true" : "false") : "none";
        }

        if (b.type == BS_TYPE_STRING) {
            str_b = b.as.string_val;
        } else if (b.type == BS_TYPE_NUMBER) {
            snprintf(buffer_b, sizeof(buffer_b), "%g", b.as.number_val);
            str_b = buffer_b;
        } else {
            str_b = (b.type == BS_TYPE_BOOL) 
                ? (b.as.boolean_val ? "true" : "false") : "none";
        }

        size_t len = strlen(str_a) + strlen(str_b) + 1;
        char* combined = (char*)malloc(len);
        strcpy(combined, str_a);
        strcat(combined, str_b);

        BSharpValue result = bsharp_make_string(combined);
        free(combined);
        return result;
    }

    bsharp_panic("Runtime Error: Invalid operands for '+' operator.");
    return bsharp_make_none();
}

BSharpValue bsharp_sub(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_number(a.as.number_val - b.as.number_val);
    }
    bsharp_panic("Runtime Error: Operands for '-' must be numbers.");
    return bsharp_make_none();
}

BSharpValue bsharp_mul(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_number(a.as.number_val * b.as.number_val);
    }
    bsharp_panic("Runtime Error: Operands for '*' must be numbers.");
    return bsharp_make_none();
}

BSharpValue bsharp_div(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        if (b.as.number_val == 0.0) {
            bsharp_panic("Runtime Error: Division by zero.");
        }
        return bsharp_make_number(a.as.number_val / b.as.number_val);
    }
    bsharp_panic("Runtime Error: Operands for '/' must be numbers.");
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
            return val.as.string_val != NULL && strlen(val.as.string_val) > 0;
        default:
            return true;
    }
}

BSharpValue bsharp_compare_eq(BSharpValue a, BSharpValue b) {
    if (a.type != b.type) return bsharp_make_bool(false);
    
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
    bsharp_panic("Runtime Error: Comparison '<' supported only for numbers.");
    return bsharp_make_bool(false);
}

BSharpValue bsharp_compare_gt(BSharpValue a, BSharpValue b) {
    if (a.type == BS_TYPE_NUMBER && b.type == BS_TYPE_NUMBER) {
        return bsharp_make_bool(a.as.number_val > b.as.number_val);
    }
    bsharp_panic("Runtime Error: Comparison '>' supported only for numbers.");
    return bsharp_make_bool(false);
}

void bsharp_print_value(BSharpValue val, bool newline) {
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
        default:
            printf("<object at %p>", val.as.ptr_val);
            break;
    }
    if (newline) {
        printf("\n");
    }
    fflush(stdout);
}

void bsharp_panic(const char* message) {
    fprintf(stderr, "B# Execution Panic: %s\n", message);
    exit(1);
}