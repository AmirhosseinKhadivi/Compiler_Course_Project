# Sea++ Compiler Course Project

This project implements the first two phases of a compiler front end for the Sea++ language.

## Implemented features

### Phase 1: Lexer

- Keywords and identifiers
- Integer, float, double, and string literals
- Arithmetic, relational, logical, assignment, increment/decrement, and member-access operators
- Delimiters
- Single-line and multi-line comments
- Accurate line and column tracking
- Lexical error reporting

### Phase 2: Parser

- Classes and functions
- Variable declarations and initialization
- `if`, `else if`, and `else`
- `while` and `for`
- Function and method calls
- Return statements
- Assignments and update expressions
- Operator precedence and constant math evaluation
- Exactly one `main` function with no parameters
- Nested scopes

### Bonus features

- AST construction
- Duplicate class and function detection
- Duplicate variable detection in the same scope
- Function existence validation
- Function argument count validation
- Function argument type validation
- Cyclic class-dependency detection using DFS

## Run the lexer

```bash
python -m src.main samples/phase1_sample.sea -o output/tokens.txt
```

## Run the parser

```bash
python -m src.parser_main samples/phase2_sample.sea -o output/parser_output.txt
```

## Generate AST files

```bash
python -m src.parser_main samples/phase2_sample.sea \
  -o output/parser_output.txt \
  --ast-output output/ast.json \
  --ast-tree-output output/ast_tree.txt
```

## Run the bonus sample

```bash
python -m src.parser_main samples/phase2_bonus_test.sea \
  -o output/parser_bonus_output.txt \
  --ast-output output/bonus_ast.json \
  --ast-tree-output output/bonus_ast_tree.txt
```

## Run tests

```bash
python -m unittest -q
```

or:

```bash
python -m pytest -q
```