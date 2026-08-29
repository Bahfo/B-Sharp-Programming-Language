##### (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

This file holds Operations Orders for B-Sharp Programming Language. Here, all expressions, terms, and factors are written with the rules assigned to each.

## Grammar (precedence from lowest to highest)

```
EXPR      : OR_EXPR
OR_EXPR   : AND_EXPR ("or" AND_EXPR)*          left-assoc, short-circuits on true
AND_EXPR  : CMP ("and" CMP)*                   left-assoc, short-circuits on false
CMP       : TERM ((==|!=|<|>|<=|>=) TERM)?     single comparison only;
                                                chained comparisons are a syntax error
TERM      : FACTOR ((+|-) FACTOR)*             left-assoc
FACTOR    : UNARY ((*|/|%|~) UNARY)*           left-assoc
UNARY     : (+|-|"not") UNARY | POWER          recursive prefix
POWER     : POSTFIX (^ UNARY)?                 right-assoc via unary recursion
POSTFIX   : POSTFIX "(" args ")"               function/method call
          | POSTFIX "[" EXPR "]"               index access
          | POSTFIX "[" [EXPR] ".." [EXPR] "]" slice
          | POSTFIX "." IDENTIFIER             property access (.length/.size/.type)
          | POSTFIX "." IDENTIFIER "(" args ")" method call
ATOM      : INT | FLOAT | STRING | BOOL | "nan" | "inf" | IDENTIFIER
          | "(" EXPR ")"
          | "[" elements "]"                   list literal
```

Notes:
- `%` and `~` share the same precedence level as `*` and `/`.
- The right operand of `^` is parsed as a unary expression, so `2 ^ -3 ^ 2`
  groups as `2 ^ (-(3 ^ 2))`.
- Comparisons never chain: write `(1 < x) and (x < 9)`.

## Operator semantics

### Arithmetic

| Op  | Name              | Semantics                                                        |
|-----|-------------------|------------------------------------------------------------------|
| +   | addition          | Numbers add; Strings concatenate.                                |
| -   | subtraction       | Numbers only.                                                    |
| *   | multiplication    | Number*Number; String*int repeats; see containers below.         |
| /   | division          | Number / Number (true division); dividing by zero is an error.   |
| %   | integer division  | C-style: truncates toward zero (`-7 % 2 == -3`). Integers only; `% 0` is an error. |
| ~   | modulo            | C-style: result takes the sign of the dividend (`-7 ~ 2 == -1`). Integers only; `~ 0` is an error. |
| ^   | power             | Right-associative. Exact for small integers; huge results fall back to float or report a clean error instead of hanging. |

Unary `-` negates Numbers, flips the sign of an infinity (`-inf` is a
first-class value, repr `-inf`), and distributes element-wise over lists
and arrays. Any other operand type reports a clear
`Unary '-' cannot negate <Type>` error.

### Comparison & logic

| Op        | Semantics                                                                                     |
|-----------|-----------------------------------------------------------------------------------------------|
| == / !=   | Numeric equality across int/float/bool. Infinities are equal only to another infinity of the SAME sign (`inf == -inf` is false). `nan` compares unequal to everything, including itself. |
| < > <= >= | Numeric ordering over Number/Boolean and both infinities (Booleans coerce to 0/1; huge exact integers order beyond the finite float range): `-inf < x <= x < inf` for every finite x. NaN has no position on the number line and poisons every ordering comparison to false on either side. Strings compare lexically. Other types compare false. |
| and / or  | Boolean-only operands; short-circuit evaluation.                                              |
| not       | Boolean operand only.                                                                          |

### Containers (List / typed Array)

Multiplication and division are element-wise:

- `list * list`: same-size lists multiply pair-wise.
- `list * number` and `number * list`: scalar-vector form, both directions.
- `list / number`: divides every element by the scalar.
- `list / list`: not supported (clean error).

Refusal rule: if an individual element refuses an operation (e.g. `"x" * 3`
is fine, but `true * 3` is not), that element is kept unchanged in the
result — the container keeps its size and no error is raised.

Slices `[start..end]` accept negative indices (Python-style wrap-around)
and clamp out-of-range bounds. Open forms `[..end]` and `[start..]` are
allowed. Slicing a typed Array returns the same array type.

### List methods (operate on the SAME object)

| Method            | Effect                                                        | Returns        |
|-------------------|---------------------------------------------------------------|----------------|
| `push(x)`         | Appends `x`.                                                  | empty          |
| `push(x, i)`      | Inserts `x` at index `i` (negative `i` wraps; `0..len` valid).| empty          |
| `append(x)`       | Appends `x`.                                                  | empty          |
| `swap(x, i)`      | Replaces the element at `i`.                                  | empty          |
| `delete(i)`       | Removes the element at `i`.                                   | empty          |
| `drop(start,end)` | Removes slice `[start:end]`.                                  | removed slice as a new List |

All index arguments must be integer Numbers. Typed Arrays validate the
element type for `push`, `append`, and `swap`.

### Properties

- `.length` / `.size`: element or character count of Lists, Arrays and Strings.
- `.type`: type name of any value.
