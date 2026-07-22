"""Token type definitions for the Sea++ lexer and parser."""

from enum import Enum, auto


class TokenType(Enum):
    """All token categories recognized by the Sea++ front end."""

    # General tokens
    KEYWORD = auto()
    IDENTIFIER = auto()

    # Literals
    INTEGER_LITERAL = auto()
    FLOAT_LITERAL = auto()
    DOUBLE_LITERAL = auto()
    STRING_LITERAL = auto()

    # Arithmetic operators
    PLUS = auto()
    MINUS = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()

    # Increment and decrement
    INCREMENT = auto()
    DECREMENT = auto()

    # Relational operators
    LESS_THAN = auto()
    GREATER_THAN = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()
    EQUAL = auto()
    NOT_EQUAL = auto()

    # Logical operators
    LOGICAL_AND = auto()
    LOGICAL_OR = auto()
    LOGICAL_NOT = auto()

    # Assignment and member access
    ASSIGN = auto()
    MEMBER_ACCESS = auto()

    # Delimiters
    SEMICOLON = auto()
    COMMA = auto()
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACKET = auto()
    RIGHT_BRACKET = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    QUESTION_MARK = auto()
    COLON = auto()

    # End of input
    EOF = auto()