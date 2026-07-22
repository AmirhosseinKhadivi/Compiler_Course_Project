"""Lexical analyzer for the Sea++ programming language."""

from src.sea_token import Token
from src.token_type import TokenType


KEYWORDS = frozenset(
    {
        "begin",
        "bool",
        "break",
        "case",
        "char",
        "class",
        "do",
        "double",
        "else",
        "end",
        "false",
        "float",
        "for",
        "if",
        "int",
        "return",
        "string",
        "switch",
        "true",
        "try",
        "void",
        "while",
    }
)


TWO_CHARACTER_TOKENS = {
    "++": TokenType.INCREMENT,
    "--": TokenType.DECREMENT,
    "<=": TokenType.LESS_EQUAL,
    ">=": TokenType.GREATER_EQUAL,
    "==": TokenType.EQUAL,
    "!=": TokenType.NOT_EQUAL,
    "&&": TokenType.LOGICAL_AND,
    "||": TokenType.LOGICAL_OR,
}


SINGLE_CHARACTER_TOKENS = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.MULTIPLY,
    "/": TokenType.DIVIDE,
    "%": TokenType.MODULO,

    "<": TokenType.LESS_THAN,
    ">": TokenType.GREATER_THAN,
    "!": TokenType.LOGICAL_NOT,
    "=": TokenType.ASSIGN,

    ".": TokenType.MEMBER_ACCESS,

    ";": TokenType.SEMICOLON,
    ",": TokenType.COMMA,

    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,

    "[": TokenType.LEFT_BRACKET,
    "]": TokenType.RIGHT_BRACKET,

    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,

    "?": TokenType.QUESTION_MARK,
    ":": TokenType.COLON,
}


class LexicalError(Exception):
    """Raised when an invalid lexical element is encountered."""


class Lexer:
    """Convert Sea++ source code into a list of tokens."""

    TAB_WIDTH = 4

    def __init__(self, source: str) -> None:
        self.source = source

        self.current_index = 0
        self.current_line = 1
        self.current_column = 1

        self.tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        """Scan the source code and return all recognized tokens."""

        while not self.is_at_end():
            character = self.current_char()

            if character in {" ", "\t", "\n", "\r"}:
                self.skip_whitespace()

            elif (
                character == "/"
                and self.peek() in {"/", "*"}
            ):
                self.skip_comment()

            elif self.is_identifier_start(character):
                self.scan_identifier_or_keyword()

            elif self.is_ascii_digit(character):
                self.scan_number()

            elif character == '"':
                self.scan_string()

            else:
                self.scan_operator_or_delimiter()

        return self.tokens

    def is_at_end(self) -> bool:
        return self.current_index >= len(self.source)

    def current_char(self) -> str:
        if self.is_at_end():
            return "\0"

        return self.source[self.current_index]

    def peek(self, offset: int = 1) -> str:
        target_index = self.current_index + offset

        if target_index >= len(self.source):
            return "\0"

        return self.source[target_index]

    def advance(self) -> str:
        character = self.current_char()

        # Windows newline: \r\n
        if character == "\r" and self.peek() == "\n":
            self.current_index += 2
            self.current_line += 1
            self.current_column = 1

            return "\n"

        if character in {"\n", "\r"}:
            self.current_index += 1
            self.current_line += 1
            self.current_column = 1

            return character

        if character == "\t":
            self.current_column += self.TAB_WIDTH
        else:
            self.current_column += 1

        self.current_index += 1

        return character

    @staticmethod
    def is_ascii_letter(character: str) -> bool:
        return (
            "a" <= character <= "z"
            or "A" <= character <= "Z"
        )

    @staticmethod
    def is_ascii_digit(character: str) -> bool:
        return "0" <= character <= "9"

    @classmethod
    def is_identifier_start(cls, character: str) -> bool:
        return (
            cls.is_ascii_letter(character)
            or character == "_"
        )

    @classmethod
    def is_identifier_part(cls, character: str) -> bool:
        return (
            cls.is_identifier_start(character)
            or cls.is_ascii_digit(character)
        )

    def skip_whitespace(self) -> None:
        while (
            not self.is_at_end()
            and self.current_char() in {" ", "\t", "\n", "\r"}
        ):
            self.advance()

    def skip_comment(self) -> None:
        start_line = self.current_line
        start_column = self.current_column

        # Single-line comment
        if self.peek() == "/":
            self.advance()
            self.advance()

            while (
                not self.is_at_end()
                and self.current_char() not in {"\n", "\r"}
            ):
                self.advance()

            return

        # Multi-line comment
        self.advance()
        self.advance()

        while not self.is_at_end():
            if (
                self.current_char() == "*"
                and self.peek() == "/"
            ):
                self.advance()
                self.advance()

                return

            self.advance()

        raise LexicalError(
            "Lexical Error: Unterminated multi-line comment "
            f"at Line {start_line}, Column {start_column}"
        )

    def scan_identifier_or_keyword(self) -> None:
        start_index = self.current_index
        start_line = self.current_line
        start_column = self.current_column

        while (
            not self.is_at_end()
            and self.is_identifier_part(self.current_char())
        ):
            self.advance()

        lexeme = self.source[
            start_index:self.current_index
        ]

        if lexeme in KEYWORDS:
            token_type = TokenType.KEYWORD
        else:
            token_type = TokenType.IDENTIFIER

        self.add_token(
            token_type,
            lexeme,
            start_line,
            start_column,
        )

    def scan_number(self) -> None:
        start_index = self.current_index
        start_line = self.current_line
        start_column = self.current_column

        while (
            not self.is_at_end()
            and self.is_ascii_digit(self.current_char())
        ):
            self.advance()

        has_decimal_point = False

        if (
            self.current_char() == "."
            and self.is_ascii_digit(self.peek())
        ):
            has_decimal_point = True
            self.advance()

            while (
                not self.is_at_end()
                and self.is_ascii_digit(self.current_char())
            ):
                self.advance()

        if (
            has_decimal_point
            and self.current_char() == "f"
        ):
            self.advance()
            token_type = TokenType.FLOAT_LITERAL

        elif has_decimal_point:
            token_type = TokenType.DOUBLE_LITERAL

        else:
            token_type = TokenType.INTEGER_LITERAL

        if self.is_identifier_part(self.current_char()):
            while (
                not self.is_at_end()
                and self.is_identifier_part(self.current_char())
            ):
                self.advance()

            invalid_lexeme = self.source[
                start_index:self.current_index
            ]

            raise LexicalError(
                "Lexical Error: Invalid numeric literal "
                f"'{invalid_lexeme}' at Line {start_line}, "
                f"Column {start_column}"
            )

        lexeme = self.source[
            start_index:self.current_index
        ]

        self.add_token(
            token_type,
            lexeme,
            start_line,
            start_column,
        )

    def scan_string(self) -> None:
        start_index = self.current_index
        start_line = self.current_line
        start_column = self.current_column

        # Opening quotation mark
        self.advance()

        while (
            not self.is_at_end()
            and self.current_char() != '"'
        ):
            self.advance()

        if self.is_at_end():
            raise LexicalError(
                "Lexical Error: Unterminated string literal "
                f"at Line {start_line}, Column {start_column}"
            )

        # Closing quotation mark
        self.advance()

        lexeme = self.source[
            start_index:self.current_index
        ]

        self.add_token(
            TokenType.STRING_LITERAL,
            lexeme,
            start_line,
            start_column,
        )

    def scan_operator_or_delimiter(self) -> None:
        start_line = self.current_line
        start_column = self.current_column

        character = self.current_char()
        two_character_lexeme = character + self.peek()

        if two_character_lexeme in TWO_CHARACTER_TOKENS:
            token_type = TWO_CHARACTER_TOKENS[
                two_character_lexeme
            ]

            self.advance()
            self.advance()

            self.add_token(
                token_type,
                two_character_lexeme,
                start_line,
                start_column,
            )

            return

        if character in SINGLE_CHARACTER_TOKENS:
            token_type = SINGLE_CHARACTER_TOKENS[
                character
            ]

            self.advance()

            self.add_token(
                token_type,
                character,
                start_line,
                start_column,
            )

            return

        raise LexicalError(
            "Lexical Error: Unexpected character "
            f"'{character}' at Line {start_line}, "
            f"Column {start_column}"
        )

    def add_token(
        self,
        token_type: TokenType,
        lexeme: str,
        line: int,
        column: int,
    ) -> None:
        self.tokens.append(
            Token(
                token_type,
                lexeme,
                line,
                column,
            )
        )