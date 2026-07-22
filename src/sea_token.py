"""Token data model and output formatting for Sea++."""

from dataclasses import dataclass

from src.token_type import TokenType


TOKEN_DISPLAY_NAMES = {
    TokenType.KEYWORD: "Keyword",
    TokenType.IDENTIFIER: "Identifier",

    TokenType.INTEGER_LITERAL: "Integer Literal",
    TokenType.FLOAT_LITERAL: "Float Literal",
    TokenType.DOUBLE_LITERAL: "Double Literal",
    TokenType.STRING_LITERAL: "String Literal",

    TokenType.PLUS: "Addition Operator",
    TokenType.MINUS: "Subtraction Operator",
    TokenType.MULTIPLY: "Multiplication Operator",
    TokenType.DIVIDE: "Division Operator",
    TokenType.MODULO: "Modulo Operator",

    TokenType.INCREMENT: "Increment Operator",
    TokenType.DECREMENT: "Decrement Operator",

    TokenType.LESS_THAN: "Less Than Operator",
    TokenType.GREATER_THAN: "Greater Than Operator",
    TokenType.LESS_EQUAL: "Less Than or Equal Operator",
    TokenType.GREATER_EQUAL: "Greater Than or Equal Operator",
    TokenType.EQUAL: "Equality Operator",
    TokenType.NOT_EQUAL: "Not Equal Operator",

    TokenType.LOGICAL_AND: "Logical AND Operator",
    TokenType.LOGICAL_OR: "Logical OR Operator",
    TokenType.LOGICAL_NOT: "Logical NOT Operator",

    TokenType.ASSIGN: "Assignment Operator",
    TokenType.MEMBER_ACCESS: "Member Access Operator",

    TokenType.SEMICOLON: "Semicolon",
    TokenType.COMMA: "Comma",
    TokenType.LEFT_PAREN: "Left Parenthesis",
    TokenType.RIGHT_PAREN: "Right Parenthesis",
    TokenType.LEFT_BRACKET: "Left Bracket",
    TokenType.RIGHT_BRACKET: "Right Bracket",
    TokenType.LEFT_BRACE: "Left Brace",
    TokenType.RIGHT_BRACE: "Right Brace",
    TokenType.QUESTION_MARK: "Question Mark",
    TokenType.COLON: "Colon",

    TokenType.EOF: "End of File",
}


@dataclass(frozen=True)
class Token:
    """One lexical token and its starting source position."""

    token_type: TokenType
    lexeme: str
    line: int
    column: int

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError(
                "Token line number must be greater than zero."
            )

        if self.column < 1:
            raise ValueError(
                "Token column number must be greater than zero."
            )

    @property
    def display_name(self) -> str:
        return TOKEN_DISPLAY_NAMES[self.token_type]

    def __str__(self) -> str:
        return (
            f"{self.display_name} ({self.lexeme})"
            f" - Line {self.line}, Column {self.column}"
        )