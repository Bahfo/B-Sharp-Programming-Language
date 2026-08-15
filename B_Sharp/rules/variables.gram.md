Variables in B-Sharp are created in one way: 
```
   var         x      =    10
KEYWORD  IDENTIFIER  EQ   EXPRESSION
Constants hold a similar pattern but with unchanged data type
  const       y      =    15
KEYWORD  IDENTIFIER  EQ   EXPRESSION
```

For both methods, grammar doesn't change, here is implementation:

`KEYWORD   IDENTIFIER  : EXPR`