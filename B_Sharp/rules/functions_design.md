# Functions Design

In B-Sharp (B#). Functions are straight-forward to be defined: 

```
fn FUNCTION_NAME (PARAMETERS) {
    EXPRESSIONS;
    return;
}
```

For example;

```
fn add_two_numbers(x, y) {
    return x + y;
}
```

Notice that a `return` statement can take a return value after it. Also, functions can accept parameters types as well.
```
fn add_two_numbers(x: Number, y: Number) {
    return x + y;
}
```

You can also assign *function output type* as well. For instance: 
```
fn add_two_numbers(x: Number, y: Number) -> Number {
    return x + y;
}
```

In addition, assigning functions to variables is also possible. In B-Sharp, this is called **shadowing**: 
```
fn add_two_numbers(x: Number, y: Number) -> Number {
    return x + y;
}

var x = add_two_numbers

// This allows `x` to take assignment of the function. Function `add_two_numbers` can be then called in two ways: 

add_two_numbers(4, 5);
x(4, 5);

// and both are valid.
```

However, you cannot, as in JavaScript or TypeScript, assign a function without calling it a name, we call this in B-Sharp **name casting**. Which is a feature that must be applied to variables, functions, and objects. For instance: 
```
fn (x, y) { // INVALID BEHAVIOR -> returns a syntax error
    // Some Expression
}

fn some_name(x, y) { // VALID
    // Some Expression
}
```

You cannot also exit a function without returning. Even if return is just `return;`. That is beause a function returns (`Empty : none`) value by default unless type is specified in definition, or in appliance.

## Definition vs. Appliance
Definition of a function is always required. In B-Sharp, definition is at the head of a function: 
```
fn function_name(parameters) -> Output_Type /// This is called Definition
{
    //// Here, this is called Appliance
}
```

Keep in mind that scope matters. Unless a `global` keyword is introduced, a function's parameters are local by default. In this version of B-Sharp. The `global` keyword is not introduced yet. Thus, all function's parameters are local.