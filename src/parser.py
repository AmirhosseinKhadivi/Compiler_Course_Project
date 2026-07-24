"""Recursive-descent parser for Phase 2 of the Sea++ project."""

from dataclasses import dataclass
from typing import Any, Callable

from src.ast_nodes import ASTNode
from src.sea_token import Token
from src.symbol_table import (
    FunctionInfo,
    ParameterInfo,
    SymbolTable,
)
from src.token_type import TokenType


BUILTIN_TYPES = {
    "int",
    "float",
    "double",
    "string",
    "bool",
    "char",
    "void",
}

VARIABLE_TYPES = BUILTIN_TYPES - {"void"}


class ParseError(Exception):
    """Raised when tokens violate the Sea++ grammar."""


@dataclass
class ExpressionResult:
    """Result of parsing and optionally evaluating an expression."""

    text: str
    value: Any = None
    type_name: str | None = None
    is_math_expression: bool = False
    node: ASTNode | None = None


@dataclass(frozen=True)
class PendingCall:
    """A function call that is validated after all definitions are known."""

    name: str
    argument_types: tuple[str | None, ...]
    token: Token
    current_class_name: str | None = None
    receiver_type: str | None = None


class Parser:
    """Parse Sea++ tokens and produce Phase 2 output messages."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = list(tokens)

        if tokens:
            last_token = tokens[-1]
            eof_line = last_token.line
            eof_column = (
                last_token.column
                + max(len(last_token.lexeme), 1)
            )
        else:
            eof_line = 1
            eof_column = 1

        self.tokens.append(
            Token(
                TokenType.EOF,
                "",
                eof_line,
                eof_column,
            )
        )

        self.current_index = 0
        self.output: list[str] = []

        self.symbols = SymbolTable()

        self.main_count = 0
        self.current_function_return_type: str | None = None
        self.current_class_name: str | None = None

        self.ast = ASTNode("Program")
        self.pending_calls: list[PendingCall] = []
        self.class_dependencies: dict[str, set[str]] = {}

    def parse(self) -> list[str]:
        """Parse a complete program and build its AST."""

        while not self.is_at_end():
            if self.check_keyword("class"):
                self.ast.add_child(
                    self.parse_class_definition()
                )

            elif self.looks_like_function_definition():
                self.ast.add_child(
                    self.parse_function_definition()
                )

            else:
                self.error_current(
                    "Expected a class or function definition."
                )

        if self.main_count != 1:
            raise ParseError(
                "Semantic Error: Program must contain "
                "exactly one main function; "
                f"found {self.main_count}."
            )

        self.validate_pending_calls()
        self.emit_cyclic_dependency_warnings()

        return self.output

    # ---------------------------------------------------------
    # Top-level definitions
    # ---------------------------------------------------------

    def parse_class_definition(self) -> ASTNode:
        """Parse a class definition and return its AST node."""

        class_token = self.consume_keyword("class")

        name_token = self.consume(
            TokenType.IDENTIFIER,
            "Expected class name.",
        )

        try:
            self.symbols.declare_class(
                name_token.lexeme
            )
        except ValueError as error:
            self.semantic_error(
                name_token,
                str(error),
            )

        self.class_dependencies.setdefault(
            name_token.lexeme,
            set(),
        )

        self.output.append(
            f"Class: {name_token.lexeme}"
        )

        self.consume_keyword("begin")

        class_node = ASTNode(
            "ClassDeclaration",
            attributes={"name": name_token.lexeme},
            line=class_token.line,
            column=class_token.column,
        )

        previous_class_name = self.current_class_name
        self.current_class_name = name_token.lexeme

        self.symbols.push_scope()

        try:
            while (
                not self.check_keyword("end")
                and not self.is_at_end()
            ):
                if self.looks_like_function_definition():
                    class_node.add_child(
                        self.parse_function_definition()
                    )

                elif self.looks_like_variable_declaration():
                    class_node.add_child(
                        self.parse_variable_declaration(
                            expect_semicolon=True
                        )
                    )

                else:
                    self.error_current(
                        "Only variable and function definitions "
                        "are allowed inside a class."
                    )

            self.consume_keyword("end")

        finally:
            self.symbols.pop_scope()
            self.current_class_name = previous_class_name

        return class_node

    def parse_function_definition(self) -> ASTNode:
        """Parse a function definition and return its AST node."""

        start_token = self.current()
        return_type = self.consume_type(
            allow_void=True
        )

        name_token = self.consume(
            TokenType.IDENTIFIER,
            "Expected function name.",
        )

        self.consume(
            TokenType.LEFT_PAREN,
            "Expected '(' after function name.",
        )

        parameters: list[ParameterInfo] = []
        parameter_nodes: list[ASTNode] = []
        parameter_tokens: list[Token] = []

        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                parameter_start = self.current()
                parameter_type = self.consume_type(
                    allow_void=False
                )

                parameter_name = self.consume(
                    TokenType.IDENTIFIER,
                    "Expected parameter name.",
                )

                parameters.append(
                    ParameterInfo(
                        parameter_type,
                        parameter_name.lexeme,
                    )
                )
                parameter_tokens.append(parameter_name)
                parameter_nodes.append(
                    ASTNode(
                        "Parameter",
                        attributes={
                            "type": parameter_type,
                            "name": parameter_name.lexeme,
                        },
                        line=parameter_start.line,
                        column=parameter_start.column,
                    )
                )

                if not self.match(TokenType.COMMA):
                    break

        self.consume(
            TokenType.RIGHT_PAREN,
            "Expected ')' after parameters.",
        )

        function_info = FunctionInfo(
            return_type=return_type,
            name=name_token.lexeme,
            parameters=tuple(parameters),
        )

        try:
            if self.current_class_name is not None:
                qualified_name = (
                    f"{self.current_class_name}."
                    f"{name_token.lexeme}"
                )
            else:
                qualified_name = name_token.lexeme

            self.symbols.declare_function(
                function_info,
                qualified_name,
            )

        except ValueError as error:
            self.semantic_error(
                name_token,
                str(error),
            )

        if name_token.lexeme == "main":
            self.main_count += 1

            if parameters:
                self.semantic_error(
                    name_token,
                    "The main function cannot accept parameters.",
                )

            if return_type not in {"void", "int"}:
                self.semantic_error(
                    name_token,
                    "The main function return type "
                    "must be void or int.",
                )

        parameter_text = ", ".join(
            f"{parameter.type_name} {parameter.name}"
            for parameter in parameters
        )

        self.output.append(
            f"Function: {return_type} "
            f"{name_token.lexeme}({parameter_text})"
        )

        function_node = ASTNode(
            "FunctionDeclaration",
            attributes={
                "name": name_token.lexeme,
                "return_type": return_type,
                "owner_class": self.current_class_name,
            },
            children=parameter_nodes,
            line=start_token.line,
            column=start_token.column,
        )

        previous_return_type = (
            self.current_function_return_type
        )

        self.current_function_return_type = return_type

        self.symbols.push_scope()

        try:
            for parameter, parameter_token in zip(
                parameters,
                parameter_tokens,
            ):
                try:
                    self.symbols.declare_variable(
                        parameter.name,
                        parameter.type_name,
                    )

                except ValueError as error:
                    self.semantic_error(
                        parameter_token,
                        str(error),
                    )

            function_node.add_child(
                self.parse_function_body()
            )

        finally:
            self.symbols.pop_scope()

            self.current_function_return_type = (
                previous_return_type
            )

        return function_node

    def parse_function_body(self) -> ASTNode:
        """Parse a function body and return a block node."""

        body_node = ASTNode("Block")

        if self.match_keyword("begin"):
            begin_token = self.previous()
            body_node.line = begin_token.line
            body_node.column = begin_token.column

            while (
                not self.check_keyword("end")
                and not self.is_at_end()
            ):
                body_node.add_child(
                    self.parse_statement()
                )

            self.consume_keyword("end")

        else:
            body_node.add_child(
                self.parse_statement()
            )

        return body_node

    # ---------------------------------------------------------
    # Statements
    # ---------------------------------------------------------

    def parse_statement(self) -> ASTNode:
        """Parse one statement and return its AST node."""

        if self.match(TokenType.SEMICOLON):
            token = self.previous()
            return ASTNode(
                "EmptyStatement",
                line=token.line,
                column=token.column,
            )

        if self.check_keyword("if"):
            return self.parse_if_statement()

        if self.check_keyword("while"):
            return self.parse_while_statement()

        if self.check_keyword("for"):
            return self.parse_for_statement()

        if self.check_keyword("return"):
            return self.parse_return_statement()

        if self.looks_like_variable_declaration():
            return self.parse_variable_declaration(
                expect_semicolon=True
            )

        if (
            self.check(TokenType.INCREMENT)
            or self.check(TokenType.DECREMENT)
        ):
            return self.parse_prefix_update(
                expect_semicolon=True
            )

        if self.check(TokenType.IDENTIFIER):
            return self.parse_identifier_statement(
                expect_semicolon=True
            )

        self.error_current(
            "Expected a valid statement."
        )

        raise AssertionError("Unreachable code.")

    def parse_variable_declaration(
        self,
        expect_semicolon: bool,
    ) -> ASTNode:
        """Parse a variable declaration and return its AST node."""

        start_token = self.current()
        type_name = self.consume_type(
            allow_void=False
        )

        name_token = self.consume(
            TokenType.IDENTIFIER,
            "Expected variable name.",
        )

        initializer: ExpressionResult | None = None

        if self.match(TokenType.ASSIGN):
            initializer = self.parse_expression()

        if expect_semicolon:
            self.consume(
                TokenType.SEMICOLON,
                "Expected ';' after variable declaration.",
            )

        if initializer is not None:
            value = initializer.value
        else:
            value = None

        try:
            self.symbols.declare_variable(
                name_token.lexeme,
                type_name,
                value,
            )

        except ValueError as error:
            self.semantic_error(
                name_token,
                str(error),
            )

        if (
            self.current_class_name is not None
            and type_name not in BUILTIN_TYPES
        ):
            self.class_dependencies.setdefault(
                self.current_class_name,
                set(),
            ).add(type_name)

        if initializer is None:
            self.output.append(
                f"Variable: {type_name} "
                f"{name_token.lexeme}"
            )

        else:
            self.output.append(
                f"Variable: {type_name} "
                f"{name_token.lexeme} = "
                f"{initializer.text}"
            )

            self.emit_math_result(initializer)

        variable_node = ASTNode(
            "VariableDeclaration",
            attributes={
                "type": type_name,
                "name": name_token.lexeme,
            },
            line=start_token.line,
            column=start_token.column,
        )

        if initializer is not None:
            variable_node.add_child(initializer.node)

        return variable_node

    def parse_if_statement(self) -> ASTNode:
        """Parse if, else-if, and else structures."""

        if_token = self.consume_keyword("if")

        self.consume(
            TokenType.LEFT_PAREN,
            "Expected '(' after if.",
        )

        condition = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Expected ')' after if condition.",
        )

        self.output.append("Conditional: if")
        self.emit_math_result(condition)

        if_node = ASTNode(
            "IfStatement",
            line=if_token.line,
            column=if_token.column,
        )

        if_branch = ASTNode(
            "IfBranch",
            children=[
                condition.node or ASTNode("UnknownExpression"),
                self.parse_control_body(),
            ],
            line=if_token.line,
            column=if_token.column,
        )
        if_node.add_child(if_branch)

        while self.match_keyword("else"):
            else_token = self.previous()

            if self.match_keyword("if"):
                self.consume(
                    TokenType.LEFT_PAREN,
                    "Expected '(' after else if.",
                )

                condition = self.parse_expression()

                self.consume(
                    TokenType.RIGHT_PAREN,
                    "Expected ')' after else-if condition.",
                )

                self.output.append(
                    "Conditional: else if"
                )

                self.emit_math_result(condition)

                if_node.add_child(
                    ASTNode(
                        "ElseIfBranch",
                        children=[
                            condition.node
                            or ASTNode("UnknownExpression"),
                            self.parse_control_body(),
                        ],
                        line=else_token.line,
                        column=else_token.column,
                    )
                )

            else:
                self.output.append(
                    "Conditional: else"
                )

                if_node.add_child(
                    ASTNode(
                        "ElseBranch",
                        children=[self.parse_control_body()],
                        line=else_token.line,
                        column=else_token.column,
                    )
                )
                break

        return if_node

    def parse_while_statement(self) -> ASTNode:
        """Parse a while loop."""

        while_token = self.consume_keyword("while")

        self.consume(
            TokenType.LEFT_PAREN,
            "Expected '(' after while.",
        )

        condition = self.parse_expression()

        self.consume(
            TokenType.RIGHT_PAREN,
            "Expected ')' after while condition.",
        )

        self.output.append("Loop: while")
        self.emit_math_result(condition)

        return ASTNode(
            "WhileStatement",
            children=[
                condition.node or ASTNode("UnknownExpression"),
                self.parse_control_body(),
            ],
            line=while_token.line,
            column=while_token.column,
        )

    def parse_for_statement(self) -> ASTNode:
        """Parse a for loop."""

        for_token = self.consume_keyword("for")
        self.output.append("Loop: for")

        self.consume(
            TokenType.LEFT_PAREN,
            "Expected '(' after for.",
        )

        for_node = ASTNode(
            "ForStatement",
            line=for_token.line,
            column=for_token.column,
        )

        self.symbols.push_scope()

        try:
            initializer_node: ASTNode | None = None
            condition: ExpressionResult | None = None
            update_node: ASTNode | None = None

            # Initializer
            if not self.check(TokenType.SEMICOLON):
                if self.looks_like_variable_declaration():
                    initializer_node = self.parse_variable_declaration(
                        expect_semicolon=False
                    )

                elif (
                    self.check(TokenType.INCREMENT)
                    or self.check(TokenType.DECREMENT)
                ):
                    initializer_node = self.parse_prefix_update(
                        expect_semicolon=False
                    )

                else:
                    initializer_node = self.parse_identifier_statement(
                        expect_semicolon=False
                    )

            self.consume(
                TokenType.SEMICOLON,
                "Expected ';' after for initializer.",
            )

            # Condition
            if not self.check(TokenType.SEMICOLON):
                condition = self.parse_expression()
                self.emit_math_result(condition)

            self.consume(
                TokenType.SEMICOLON,
                "Expected ';' after for condition.",
            )

            # Update
            if not self.check(TokenType.RIGHT_PAREN):
                if (
                    self.check(TokenType.INCREMENT)
                    or self.check(TokenType.DECREMENT)
                ):
                    update_node = self.parse_prefix_update(
                        expect_semicolon=False
                    )

                else:
                    update_node = self.parse_identifier_statement(
                        expect_semicolon=False
                    )

            self.consume(
                TokenType.RIGHT_PAREN,
                "Expected ')' after for clauses.",
            )

            for_node.add_child(
                ASTNode(
                    "ForInitializer",
                    children=(
                        [initializer_node]
                        if initializer_node is not None
                        else []
                    ),
                )
            )
            for_node.add_child(
                ASTNode(
                    "ForCondition",
                    children=(
                        [condition.node]
                        if condition is not None
                        and condition.node is not None
                        else []
                    ),
                )
            )
            for_node.add_child(
                ASTNode(
                    "ForUpdate",
                    children=(
                        [update_node]
                        if update_node is not None
                        else []
                    ),
                )
            )
            for_node.add_child(
                self.parse_control_body()
            )

        finally:
            self.symbols.pop_scope()

        return for_node

    def parse_return_statement(self) -> ASTNode:
        """Parse a return statement."""

        return_keyword = self.consume_keyword(
            "return"
        )

        expression: ExpressionResult | None = None

        if not self.check(TokenType.SEMICOLON):
            expression = self.parse_expression()

        self.consume(
            TokenType.SEMICOLON,
            "Expected ';' after return statement.",
        )

        if (
            self.current_function_return_type == "void"
            and expression is not None
        ):
            self.semantic_error(
                return_keyword,
                "A void function cannot return a value.",
            )

        if (
            self.current_function_return_type
            not in {None, "void"}
            and expression is None
        ):
            self.semantic_error(
                return_keyword,
                "A non-void function must return a value.",
            )

        return_node = ASTNode(
            "ReturnStatement",
            line=return_keyword.line,
            column=return_keyword.column,
        )

        if expression is not None:
            self.emit_math_result(expression)
            return_node.add_child(expression.node)

        return return_node

    def parse_control_body(self) -> ASTNode:
        """Parse a loop or conditional body."""

        self.symbols.push_scope()
        body_node = ASTNode("Block")

        try:
            if self.match_keyword("begin"):
                begin_token = self.previous()
                body_node.line = begin_token.line
                body_node.column = begin_token.column

                while (
                    not self.check_keyword("end")
                    and not self.is_at_end()
                ):
                    body_node.add_child(
                        self.parse_statement()
                    )

                self.consume_keyword("end")

            else:
                body_node.add_child(
                    self.parse_statement()
                )

        finally:
            self.symbols.pop_scope()

        return body_node

    def parse_identifier_statement(
        self,
        expect_semicolon: bool,
    ) -> ASTNode:
        """Parse assignment, call, increment, or decrement."""

        start_token = self.current()
        target = self.parse_identifier_path()

        if self.check(TokenType.LEFT_PAREN):
            call_result = self.finish_function_call(
                target,
                start_token,
            )
            statement_node = call_result.node or ASTNode(
                "FunctionCall",
                attributes={"name": target},
                line=start_token.line,
                column=start_token.column,
            )

        elif self.match(TokenType.ASSIGN):
            expression = self.parse_expression()

            if "." not in target:
                self.symbols.assign_variable(
                    target,
                    expression.value,
                )

            self.emit_math_result(expression)

            statement_node = ASTNode(
                "AssignmentStatement",
                children=[
                    self.make_reference_node(
                        target,
                        start_token,
                    ),
                    expression.node
                    or ASTNode("UnknownExpression"),
                ],
                line=start_token.line,
                column=start_token.column,
            )

        elif self.match(
            TokenType.INCREMENT,
            TokenType.DECREMENT,
        ):
            operator = self.previous()
            self.apply_update(target, operator)

            statement_node = ASTNode(
                "UpdateExpression",
                attributes={
                    "operator": operator.lexeme,
                    "position": "postfix",
                },
                children=[
                    self.make_reference_node(
                        target,
                        start_token,
                    )
                ],
                line=start_token.line,
                column=start_token.column,
            )

        else:
            self.error_current(
                "Expected assignment, function call, "
                "increment, or decrement."
            )
            raise AssertionError("Unreachable code.")

        if expect_semicolon:
            self.consume(
                TokenType.SEMICOLON,
                "Expected ';' after statement.",
            )

        return statement_node

    def parse_prefix_update(
        self,
        expect_semicolon: bool,
    ) -> ASTNode:
        """Parse ++x or --x."""

        operator = self.advance()
        target_token = self.current()
        target = self.parse_identifier_path()

        self.apply_update(
            target,
            operator,
        )

        if expect_semicolon:
            self.consume(
                TokenType.SEMICOLON,
                "Expected ';' after update.",
            )

        return ASTNode(
            "UpdateExpression",
            attributes={
                "operator": operator.lexeme,
                "position": "prefix",
            },
            children=[
                self.make_reference_node(
                    target,
                    target_token,
                )
            ],
            line=operator.line,
            column=operator.column,
        )

    # ---------------------------------------------------------
    # Expressions
    # ---------------------------------------------------------

    def parse_expression(self) -> ExpressionResult:
        """Parse an expression."""

        return self.parse_ternary()

    def parse_ternary(self) -> ExpressionResult:
        """Parse condition ? first : second."""

        condition = self.parse_logical_or()

        if not self.match(TokenType.QUESTION_MARK):
            return condition

        question_token = self.previous()
        when_true = self.parse_expression()

        self.consume(
            TokenType.COLON,
            "Expected ':' in ternary expression.",
        )

        when_false = self.parse_expression()

        value = None

        if condition.value is not None:
            if bool(condition.value):
                value = when_true.value
            else:
                value = when_false.value

        if when_true.type_name == when_false.type_name:
            result_type = when_true.type_name
        else:
            result_type = None

        return ExpressionResult(
            text=(
                f"{condition.text} ? "
                f"{when_true.text} : "
                f"{when_false.text}"
            ),
            value=value,
            type_name=result_type,
            is_math_expression=False,
            node=ASTNode(
                "TernaryExpression",
                children=[
                    condition.node or ASTNode("UnknownExpression"),
                    when_true.node or ASTNode("UnknownExpression"),
                    when_false.node or ASTNode("UnknownExpression"),
                ],
                line=question_token.line,
                column=question_token.column,
            ),
        )

    def parse_logical_or(self) -> ExpressionResult:
        return self.parse_left_associative(
            self.parse_logical_and,
            {TokenType.LOGICAL_OR},
            self.evaluate_binary,
        )

    def parse_logical_and(self) -> ExpressionResult:
        return self.parse_left_associative(
            self.parse_equality,
            {TokenType.LOGICAL_AND},
            self.evaluate_binary,
        )

    def parse_equality(self) -> ExpressionResult:
        return self.parse_left_associative(
            self.parse_relational,
            {
                TokenType.EQUAL,
                TokenType.NOT_EQUAL,
            },
            self.evaluate_binary,
        )

    def parse_relational(self) -> ExpressionResult:
        return self.parse_left_associative(
            self.parse_additive,
            {
                TokenType.LESS_THAN,
                TokenType.GREATER_THAN,
                TokenType.LESS_EQUAL,
                TokenType.GREATER_EQUAL,
            },
            self.evaluate_binary,
        )

    def parse_additive(self) -> ExpressionResult:
        return self.parse_left_associative(
            self.parse_multiplicative,
            {
                TokenType.PLUS,
                TokenType.MINUS,
            },
            self.evaluate_binary,
            math_level=True,
        )

    def parse_multiplicative(self) -> ExpressionResult:
        return self.parse_left_associative(
            self.parse_unary,
            {
                TokenType.MULTIPLY,
                TokenType.DIVIDE,
                TokenType.MODULO,
            },
            self.evaluate_binary,
            math_level=True,
        )

    def parse_left_associative(
        self,
        operand_parser: Callable[
            [],
            ExpressionResult,
        ],
        operators: set[TokenType],
        evaluator: Callable[
            [
                Token,
                ExpressionResult,
                ExpressionResult,
            ],
            Any,
        ],
        math_level: bool = False,
    ) -> ExpressionResult:
        """Parse left-associative binary expressions."""

        expression = operand_parser()

        while self.current().token_type in operators:
            operator = self.advance()
            right = operand_parser()
            left = expression

            value = evaluator(
                operator,
                left,
                right,
            )

            expression = ExpressionResult(
                text=(
                    f"{left.text} "
                    f"{operator.lexeme} "
                    f"{right.text}"
                ),
                value=value,
                type_name=self.infer_binary_type(
                    operator,
                    left,
                    right,
                ),
                is_math_expression=(
                    math_level
                    or left.is_math_expression
                    or right.is_math_expression
                ),
                node=ASTNode(
                    "BinaryExpression",
                    attributes={
                        "operator": operator.lexeme,
                    },
                    children=[
                        left.node or ASTNode("UnknownExpression"),
                        right.node or ASTNode("UnknownExpression"),
                    ],
                    line=operator.line,
                    column=operator.column,
                ),
            )

        return expression

    def parse_unary(self) -> ExpressionResult:
        """Parse unary operators."""

        if self.match(
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.LOGICAL_NOT,
            TokenType.INCREMENT,
            TokenType.DECREMENT,
        ):
            operator = self.previous()
            operand = self.parse_unary()

            value = self.evaluate_unary(
                operator,
                operand,
            )

            return ExpressionResult(
                text=f"{operator.lexeme}{operand.text}",
                value=value,
                type_name=operand.type_name,
                is_math_expression=(
                    operator.token_type
                    in {
                        TokenType.PLUS,
                        TokenType.MINUS,
                    }
                    or operand.is_math_expression
                ),
                node=ASTNode(
                    "UnaryExpression",
                    attributes={
                        "operator": operator.lexeme,
                        "position": "prefix",
                    },
                    children=[
                        operand.node or ASTNode("UnknownExpression")
                    ],
                    line=operator.line,
                    column=operator.column,
                ),
            )

        return self.parse_primary()

    def parse_primary(self) -> ExpressionResult:
        """Parse literals, identifiers, calls, and parentheses."""

        if self.match(TokenType.INTEGER_LITERAL):
            token = self.previous()

            return ExpressionResult(
                token.lexeme,
                int(token.lexeme),
                "int",
                node=ASTNode(
                    "Literal",
                    attributes={
                        "type": "int",
                        "value": int(token.lexeme),
                        "text": token.lexeme,
                    },
                    line=token.line,
                    column=token.column,
                ),
            )

        if self.match(TokenType.FLOAT_LITERAL):
            token = self.previous()
            value = float(token.lexeme[:-1])

            return ExpressionResult(
                token.lexeme,
                value,
                "float",
                node=ASTNode(
                    "Literal",
                    attributes={
                        "type": "float",
                        "value": value,
                        "text": token.lexeme,
                    },
                    line=token.line,
                    column=token.column,
                ),
            )

        if self.match(TokenType.DOUBLE_LITERAL):
            token = self.previous()
            value = float(token.lexeme)

            return ExpressionResult(
                token.lexeme,
                value,
                "double",
                node=ASTNode(
                    "Literal",
                    attributes={
                        "type": "double",
                        "value": value,
                        "text": token.lexeme,
                    },
                    line=token.line,
                    column=token.column,
                ),
            )

        if self.match(TokenType.STRING_LITERAL):
            token = self.previous()
            value = token.lexeme[1:-1]

            return ExpressionResult(
                token.lexeme,
                value,
                "string",
                node=ASTNode(
                    "Literal",
                    attributes={
                        "type": "string",
                        "value": value,
                        "text": token.lexeme,
                    },
                    line=token.line,
                    column=token.column,
                ),
            )

        if self.match_keyword("true"):
            token = self.previous()
            return ExpressionResult(
                "true",
                True,
                "bool",
                node=ASTNode(
                    "Literal",
                    attributes={
                        "type": "bool",
                        "value": True,
                        "text": "true",
                    },
                    line=token.line,
                    column=token.column,
                ),
            )

        if self.match_keyword("false"):
            token = self.previous()
            return ExpressionResult(
                "false",
                False,
                "bool",
                node=ASTNode(
                    "Literal",
                    attributes={
                        "type": "bool",
                        "value": False,
                        "text": "false",
                    },
                    line=token.line,
                    column=token.column,
                ),
            )

        if self.match(TokenType.LEFT_PAREN):
            left_paren = self.previous()
            inner = self.parse_expression()

            self.consume(
                TokenType.RIGHT_PAREN,
                "Expected ')' after expression.",
            )

            return ExpressionResult(
                text=f"({inner.text})",
                value=inner.value,
                type_name=inner.type_name,
                is_math_expression=(
                    inner.is_math_expression
                ),
                node=ASTNode(
                    "GroupedExpression",
                    children=[
                        inner.node or ASTNode("UnknownExpression")
                    ],
                    line=left_paren.line,
                    column=left_paren.column,
                ),
            )

        if self.check(TokenType.IDENTIFIER):
            start_token = self.current()
            path = self.parse_identifier_path()

            if self.check(TokenType.LEFT_PAREN):
                return self.finish_function_call(
                    path,
                    start_token,
                )

            if "." not in path:
                variable_info = (
                    self.symbols.lookup_variable(path)
                )
            else:
                variable_info = None

            result = ExpressionResult(
                text=path,
                value=(
                    variable_info.value
                    if variable_info is not None
                    else None
                ),
                type_name=(
                    variable_info.type_name
                    if variable_info is not None
                    else None
                ),
                node=self.make_reference_node(
                    path,
                    start_token,
                ),
            )

            if self.match(
                TokenType.INCREMENT,
                TokenType.DECREMENT,
            ):
                operator = self.previous()
                old_value = result.value

                self.apply_update(
                    path,
                    operator,
                )

                return ExpressionResult(
                    text=f"{path}{operator.lexeme}",
                    value=old_value,
                    type_name=result.type_name,
                    node=ASTNode(
                        "UpdateExpression",
                        attributes={
                            "operator": operator.lexeme,
                            "position": "postfix",
                        },
                        children=[
                            result.node
                            or ASTNode("UnknownExpression")
                        ],
                        line=start_token.line,
                        column=start_token.column,
                    ),
                )

            return result

        self.error_current(
            "Expected an expression."
        )

        raise AssertionError("Unreachable code.")

    def finish_function_call(
        self,
        function_name: str,
        name_token: Token,
    ) -> ExpressionResult:
        """Complete parsing of a function call."""

        self.consume(
            TokenType.LEFT_PAREN,
            "Expected '(' in function call.",
        )

        arguments: list[ExpressionResult] = []

        if not self.check(TokenType.RIGHT_PAREN):
            while True:
                argument = self.parse_expression()

                arguments.append(argument)
                self.emit_math_result(argument)

                if not self.match(TokenType.COMMA):
                    break

        self.consume(
            TokenType.RIGHT_PAREN,
            "Expected ')' after arguments.",
        )

        argument_text = ", ".join(
            argument.text
            for argument in arguments
        )

        self.output.append(
            f"Call: {function_name}({argument_text})"
        )

        receiver_type: str | None = None

        if "." in function_name:
            receiver_name = function_name.split(".", 1)[0]
            receiver_info = self.symbols.lookup_variable(
                receiver_name
            )

            if receiver_info is not None:
                receiver_type = receiver_info.type_name

        self.pending_calls.append(
            PendingCall(
                name=function_name,
                argument_types=tuple(
                    argument.type_name
                    for argument in arguments
                ),
                token=name_token,
                current_class_name=self.current_class_name,
                receiver_type=receiver_type,
            )
        )

        function_info = self.resolve_function_info(
            function_name=function_name,
            current_class_name=self.current_class_name,
            receiver_type=receiver_type,
        )

        call_node = ASTNode(
            "FunctionCall",
            attributes={
                "name": function_name,
            },
            children=[
                argument.node or ASTNode("UnknownExpression")
                for argument in arguments
            ],
            line=name_token.line,
            column=name_token.column,
        )

        return ExpressionResult(
            text=f"{function_name}({argument_text})",
            value=None,
            type_name=(
                function_info.return_type
                if function_info is not None
                else None
            ),
            node=call_node,
        )

    # ---------------------------------------------------------
    # Evaluation and symbols
    # ---------------------------------------------------------

    def evaluate_binary(
        self,
        operator: Token,
        left: ExpressionResult,
        right: ExpressionResult,
    ) -> Any:
        """Evaluate a constant binary expression."""

        if left.value is None or right.value is None:
            return None

        try:
            operations = {
                TokenType.PLUS:
                    lambda: left.value + right.value,

                TokenType.MINUS:
                    lambda: left.value - right.value,

                TokenType.MULTIPLY:
                    lambda: left.value * right.value,

                TokenType.DIVIDE:
                    lambda: left.value / right.value,

                TokenType.MODULO:
                    lambda: left.value % right.value,

                TokenType.LESS_THAN:
                    lambda: left.value < right.value,

                TokenType.GREATER_THAN:
                    lambda: left.value > right.value,

                TokenType.LESS_EQUAL:
                    lambda: left.value <= right.value,

                TokenType.GREATER_EQUAL:
                    lambda: left.value >= right.value,

                TokenType.EQUAL:
                    lambda: left.value == right.value,

                TokenType.NOT_EQUAL:
                    lambda: left.value != right.value,

                TokenType.LOGICAL_AND:
                    lambda: (
                        bool(left.value)
                        and bool(right.value)
                    ),

                TokenType.LOGICAL_OR:
                    lambda: (
                        bool(left.value)
                        or bool(right.value)
                    ),
            }

            return operations[operator.token_type]()

        except ZeroDivisionError:
            self.semantic_error(
                operator,
                "Division by zero in constant expression.",
            )

        except (TypeError, ValueError):
            return None

    def evaluate_unary(
        self,
        operator: Token,
        operand: ExpressionResult,
    ) -> Any:
        """Evaluate a constant unary expression."""

        if operand.value is None:
            return None

        if operator.token_type is TokenType.PLUS:
            return +operand.value

        if operator.token_type is TokenType.MINUS:
            return -operand.value

        if operator.token_type is TokenType.LOGICAL_NOT:
            return not bool(operand.value)

        if operator.token_type is TokenType.INCREMENT:
            return operand.value + 1

        if operator.token_type is TokenType.DECREMENT:
            return operand.value - 1

        return None

    @staticmethod
    def infer_binary_type(
        operator: Token,
        left: ExpressionResult,
        right: ExpressionResult,
    ) -> str | None:
        """Infer the resulting type of a binary expression."""

        if operator.token_type in {
            TokenType.LESS_THAN,
            TokenType.GREATER_THAN,
            TokenType.LESS_EQUAL,
            TokenType.GREATER_EQUAL,
            TokenType.EQUAL,
            TokenType.NOT_EQUAL,
            TokenType.LOGICAL_AND,
            TokenType.LOGICAL_OR,
        }:
            return "bool"

        if "double" in {
            left.type_name,
            right.type_name,
        }:
            return "double"

        if "float" in {
            left.type_name,
            right.type_name,
        }:
            return "float"

        if left.type_name == right.type_name:
            return left.type_name

        return None

    def apply_update(
        self,
        target: str,
        operator: Token,
    ) -> None:
        """Apply ++ or -- to a known numeric variable."""

        if "." in target:
            return

        variable_info = (
            self.symbols.lookup_variable(target)
        )

        if (
            variable_info is None
            or variable_info.value is None
        ):
            return

        try:
            if operator.token_type is TokenType.INCREMENT:
                delta = 1
            else:
                delta = -1

            self.symbols.assign_variable(
                target,
                variable_info.value + delta,
            )

        except TypeError:
            self.semantic_error(
                operator,
                f"Cannot update non-numeric variable "
                f"'{target}'.",
            )

    def emit_math_result(
        self,
        expression: ExpressionResult,
    ) -> None:
        """Print evaluated mathematical expressions."""

        numeric_types = {
            "int",
            "float",
            "double",
        }

        if (
            expression.is_math_expression
            and expression.value is not None
            and expression.type_name in numeric_types
            and not isinstance(expression.value, bool)
        ):
            self.output.append(
                "Math Expression Result: "
                f"{self.format_value(expression.value)}"
            )

    @staticmethod
    def format_value(value: Any) -> str:
        """Format calculated values for output."""

        if isinstance(value, bool):
            return "true" if value else "false"

        if (
            isinstance(value, float)
            and value.is_integer()
        ):
            return str(int(value))

        return str(value)

    def make_reference_node(
        self,
        path: str,
        token: Token,
    ) -> ASTNode:
        """Create an identifier or member-access AST node."""

        if "." not in path:
            return ASTNode(
                "Identifier",
                attributes={"name": path},
                line=token.line,
                column=token.column,
            )

        parts = path.split(".")

        return ASTNode(
            "MemberAccess",
            attributes={
                "path": path,
                "object": parts[0],
                "member": parts[-1],
            },
            line=token.line,
            column=token.column,
        )

    def resolve_function_info(
        self,
        function_name: str,
        current_class_name: str | None,
        receiver_type: str | None,
    ) -> FunctionInfo | None:
        """Resolve a global function or class method."""

        if function_name == "print":
            return FunctionInfo(
                return_type="void",
                name="print",
                parameters=(),
            )

        if "." in function_name:
            receiver_name, method_name = function_name.split(
                ".",
                1,
            )

            if receiver_type is not None:
                return self.symbols.lookup_function(
                    f"{receiver_type}.{method_name}"
                )

            if self.symbols.has_class(receiver_name):
                return self.symbols.lookup_function(
                    f"{receiver_name}.{method_name}"
                )

            return None

        if current_class_name is not None:
            method = self.symbols.lookup_function(
                f"{current_class_name}.{function_name}"
            )

            if method is not None:
                return method

        return self.symbols.lookup_function(function_name)

    def validate_pending_calls(self) -> None:
        """Validate function existence, argument count, and argument types."""

        for call in self.pending_calls:
            if call.name == "print":
                continue

            function_info = self.resolve_function_info(
                function_name=call.name,
                current_class_name=call.current_class_name,
                receiver_type=call.receiver_type,
            )

            if function_info is None:
                self.semantic_error(
                    call.token,
                    f"Function '{call.name}' is not defined.",
                )

            expected_count = len(function_info.parameters)
            actual_count = len(call.argument_types)

            if expected_count != actual_count:
                self.semantic_error(
                    call.token,
                    f"Function '{call.name}' expects "
                    f"{expected_count} argument(s), but "
                    f"{actual_count} were provided.",
                )

            for index, (argument_type, parameter) in enumerate(
                zip(
                    call.argument_types,
                    function_info.parameters,
                ),
                start=1,
            ):
                if argument_type is None:
                    continue

                if not self.is_type_compatible(
                    argument_type,
                    parameter.type_name,
                ):
                    self.semantic_error(
                        call.token,
                        f"Argument {index} of function "
                        f"'{call.name}' has type "
                        f"'{argument_type}', but "
                        f"'{parameter.type_name}' was expected.",
                    )

    @staticmethod
    def is_type_compatible(
        argument_type: str,
        parameter_type: str,
    ) -> bool:
        """Check direct matches and safe numeric widening conversions."""

        if argument_type == parameter_type:
            return True

        safe_numeric_conversions = {
            ("int", "float"),
            ("int", "double"),
            ("float", "double"),
        }

        return (
            argument_type,
            parameter_type,
        ) in safe_numeric_conversions

    def emit_cyclic_dependency_warnings(self) -> None:
        """Find cycles in the class-dependency graph using DFS."""

        states: dict[str, str] = {
            class_name: "white"
            for class_name in self.symbols.classes
        }
        stack: list[str] = []
        reported_cycles: set[frozenset[str]] = set()

        def visit(class_name: str) -> None:
            states[class_name] = "gray"
            stack.append(class_name)

            for dependency in sorted(
                self.class_dependencies.get(
                    class_name,
                    set(),
                )
            ):
                if dependency not in self.symbols.classes:
                    continue

                dependency_state = states[dependency]

                if dependency_state == "white":
                    visit(dependency)

                elif dependency_state == "gray":
                    cycle_start = stack.index(dependency)
                    cycle = stack[cycle_start:] + [dependency]
                    cycle_classes = frozenset(cycle[:-1])

                    if cycle_classes in reported_cycles:
                        continue

                    reported_cycles.add(cycle_classes)

                    if len(cycle_classes) == 2:
                        first, second = cycle[:-1]
                        self.output.append(
                            "Warning: Cyclic dependency detected "
                            f"between class {first} and class {second}."
                        )
                    else:
                        self.output.append(
                            "Warning: Cyclic dependency detected: "
                            + " -> ".join(cycle)
                            + "."
                        )

            stack.pop()
            states[class_name] = "black"

        for class_name in sorted(self.symbols.classes):
            if states[class_name] == "white":
                visit(class_name)

    # ---------------------------------------------------------
    # Token helpers
    # ---------------------------------------------------------

    def looks_like_function_definition(self) -> bool:
        """Check whether upcoming tokens form a function."""

        if not self.is_type_token(
            self.current(),
            allow_void=True,
        ):
            return False

        return (
            self.peek_token(1).token_type
            is TokenType.IDENTIFIER

            and self.peek_token(2).token_type
            is TokenType.LEFT_PAREN
        )

    def looks_like_variable_declaration(self) -> bool:
        """Check whether upcoming tokens form a variable."""

        if not self.is_type_token(
            self.current(),
            allow_void=False,
        ):
            return False

        return (
            self.peek_token(1).token_type
            is TokenType.IDENTIFIER
        )

    def is_type_token(
        self,
        token: Token,
        allow_void: bool,
    ) -> bool:
        """Check whether a token can represent a type."""

        # Class names are identifiers and may be used as types.
        if token.token_type is TokenType.IDENTIFIER:
            return True

        if token.token_type is not TokenType.KEYWORD:
            return False

        if allow_void:
            allowed_types = BUILTIN_TYPES
        else:
            allowed_types = VARIABLE_TYPES

        return token.lexeme in allowed_types

    def consume_type(self, allow_void: bool) -> str:
        """Consume and return a valid type."""

        token = self.current()

        if self.is_type_token(
            token,
            allow_void=allow_void,
        ):
            self.advance()
            return token.lexeme

        self.error_current(
            "Expected a valid type."
        )

        raise AssertionError("Unreachable code.")

    def parse_identifier_path(self) -> str:
        """Parse object.member paths."""

        first_identifier = self.consume(
            TokenType.IDENTIFIER,
            "Expected identifier.",
        )

        parts = [first_identifier.lexeme]

        while self.match(TokenType.MEMBER_ACCESS):
            member = self.consume(
                TokenType.IDENTIFIER,
                "Expected member name after '.'.",
            )

            parts.append(member.lexeme)

        return ".".join(parts)

    def current(self) -> Token:
        return self.tokens[self.current_index]

    def peek_token(self, offset: int) -> Token:
        index = min(
            self.current_index + offset,
            len(self.tokens) - 1,
        )

        return self.tokens[index]

    def previous(self) -> Token:
        return self.tokens[self.current_index - 1]

    def is_at_end(self) -> bool:
        return (
            self.current().token_type
            is TokenType.EOF
        )

    def advance(self) -> Token:
        token = self.current()

        if not self.is_at_end():
            self.current_index += 1

        return token

    def check(self, token_type: TokenType) -> bool:
        return (
            self.current().token_type
            is token_type
        )

    def match(
        self,
        *token_types: TokenType,
    ) -> bool:
        if self.current().token_type in token_types:
            self.advance()
            return True

        return False

    def check_keyword(self, keyword: str) -> bool:
        token = self.current()

        return (
            token.token_type is TokenType.KEYWORD
            and token.lexeme == keyword
        )

    def match_keyword(self, keyword: str) -> bool:
        if self.check_keyword(keyword):
            self.advance()
            return True

        return False

    def consume(
        self,
        token_type: TokenType,
        message: str,
    ) -> Token:
        if self.check(token_type):
            return self.advance()

        self.error_current(message)

        raise AssertionError("Unreachable code.")

    def consume_keyword(self, keyword: str) -> Token:
        if self.check_keyword(keyword):
            return self.advance()

        self.error_current(
            f"Expected keyword '{keyword}'."
        )

        raise AssertionError("Unreachable code.")

    def error_current(self, message: str) -> None:
        token = self.current()

        if token.token_type is TokenType.EOF:
            found = "end of file"
        else:
            found = repr(token.lexeme)

        raise ParseError(
            f"Syntax Error: {message} "
            f"Found {found} at Line {token.line}, "
            f"Column {token.column}."
        )

    @staticmethod
    def semantic_error(
        token: Token,
        message: str,
    ) -> None:
        raise ParseError(
            f"Semantic Error: {message} "
            f"at Line {token.line}, "
            f"Column {token.column}."
        )
