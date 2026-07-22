"""
Automated tests for the Sea++ Phase 1 lexical analyzer.
"""

import unittest

from src.lexer import KEYWORDS, Lexer, LexicalError
from src.token_type import TokenType


class LexerTests(unittest.TestCase):
    """Tests for all required lexical categories."""

    @staticmethod
    def token_pairs(
        source: str,
    ) -> list[tuple[TokenType, str]]:
        """Return token type and lexeme pairs."""

        return [
            (token.token_type, token.lexeme)
            for token in Lexer(source).tokenize()
        ]

    def test_all_keywords(self) -> None:
        source = " ".join(sorted(KEYWORDS))
        tokens = Lexer(source).tokenize()

        self.assertEqual(
            len(tokens),
            len(KEYWORDS),
        )

        self.assertTrue(
            all(
                token.token_type is TokenType.KEYWORD
                for token in tokens
            )
        )

    def test_identifiers(self) -> None:
        actual = self.token_pairs(
            "_value MyClass value2 beginning intValue"
        )

        expected = [
            (TokenType.IDENTIFIER, "_value"),
            (TokenType.IDENTIFIER, "MyClass"),
            (TokenType.IDENTIFIER, "value2"),
            (TokenType.IDENTIFIER, "beginning"),
            (TokenType.IDENTIFIER, "intValue"),
        ]

        self.assertEqual(actual, expected)

    def test_numeric_literals(self) -> None:
        actual = self.token_pairs(
            "0 42 0.0 9.0134 0.211f 9.2481f"
        )

        expected = [
            (TokenType.INTEGER_LITERAL, "0"),
            (TokenType.INTEGER_LITERAL, "42"),
            (TokenType.DOUBLE_LITERAL, "0.0"),
            (TokenType.DOUBLE_LITERAL, "9.0134"),
            (TokenType.FLOAT_LITERAL, "0.211f"),
            (TokenType.FLOAT_LITERAL, "9.2481f"),
        ]

        self.assertEqual(actual, expected)

    def test_string_literals(self) -> None:
        actual = self.token_pairs(
            '"Hello world!" "" "Sea++"'
        )

        expected = [
            (
                TokenType.STRING_LITERAL,
                '"Hello world!"',
            ),
            (
                TokenType.STRING_LITERAL,
                '""',
            ),
            (
                TokenType.STRING_LITERAL,
                '"Sea++"',
            ),
        ]

        self.assertEqual(actual, expected)

    def test_operators_and_delimiters(self) -> None:
        source = (
            "+ - * / % ++ -- "
            "< > <= >= == != "
            "&& || ! = . "
            "; , ( ) [ ] { }"
        )

        tokens = Lexer(source).tokenize()

        expected_types = [
            TokenType.PLUS,
            TokenType.MINUS,
            TokenType.MULTIPLY,
            TokenType.DIVIDE,
            TokenType.MODULO,

            TokenType.INCREMENT,
            TokenType.DECREMENT,

            TokenType.LESS_THAN,
            TokenType.GREATER_THAN,
            TokenType.LESS_EQUAL,
            TokenType.GREATER_EQUAL,
            TokenType.EQUAL,
            TokenType.NOT_EQUAL,

            TokenType.LOGICAL_AND,
            TokenType.LOGICAL_OR,
            TokenType.LOGICAL_NOT,

            TokenType.ASSIGN,
            TokenType.MEMBER_ACCESS,

            TokenType.SEMICOLON,
            TokenType.COMMA,
            TokenType.LEFT_PAREN,
            TokenType.RIGHT_PAREN,
            TokenType.LEFT_BRACKET,
            TokenType.RIGHT_BRACKET,
            TokenType.LEFT_BRACE,
            TokenType.RIGHT_BRACE,
        ]

        actual_types = [
            token.token_type
            for token in tokens
        ]

        self.assertEqual(
            actual_types,
            expected_types,
        )

    def test_line_column_and_tab(self) -> None:
        source = "class X\r\n\tint value"
        tokens = Lexer(source).tokenize()

        positions = [
            (
                token.lexeme,
                token.line,
                token.column,
            )
            for token in tokens
        ]

        expected = [
            ("class", 1, 1),
            ("X", 1, 7),
            ("int", 2, 5),
            ("value", 2, 9),
        ]

        self.assertEqual(
            positions,
            expected,
        )

    def test_single_line_comment(self) -> None:
        source = (
            "int x; // ignored comment\n"
            "float y;"
        )

        tokens = Lexer(source).tokenize()

        actual_lexemes = [
            token.lexeme
            for token in tokens
        ]

        expected_lexemes = [
            "int",
            "x",
            ";",
            "float",
            "y",
            ";",
        ]

        self.assertEqual(
            actual_lexemes,
            expected_lexemes,
        )

    def test_multi_line_comment(self) -> None:
        source = (
            "int x; /* first line\n"
            "second line */\n"
            "float y;"
        )

        tokens = Lexer(source).tokenize()

        actual_lexemes = [
            token.lexeme
            for token in tokens
        ]

        expected_lexemes = [
            "int",
            "x",
            ";",
            "float",
            "y",
            ";",
        ]

        self.assertEqual(
            actual_lexemes,
            expected_lexemes,
        )

        float_token = tokens[3]

        self.assertEqual(
            (
                float_token.line,
                float_token.column,
            ),
            (3, 1),
        )

    def test_division_is_not_comment(self) -> None:
        actual = self.token_pairs("10 / 2")

        expected = [
            (TokenType.INTEGER_LITERAL, "10"),
            (TokenType.DIVIDE, "/"),
            (TokenType.INTEGER_LITERAL, "2"),
        ]

        self.assertEqual(actual, expected)

    def test_member_access(self) -> None:
        actual = self.token_pairs(
            "myClassInstance.set_value(10);"
        )

        expected = [
            (
                TokenType.IDENTIFIER,
                "myClassInstance",
            ),
            (
                TokenType.MEMBER_ACCESS,
                ".",
            ),
            (
                TokenType.IDENTIFIER,
                "set_value",
            ),
            (
                TokenType.LEFT_PAREN,
                "(",
            ),
            (
                TokenType.INTEGER_LITERAL,
                "10",
            ),
            (
                TokenType.RIGHT_PAREN,
                ")",
            ),
            (
                TokenType.SEMICOLON,
                ";",
            ),
        ]

        self.assertEqual(actual, expected)

    def test_output_format(self) -> None:
        token = Lexer("class").tokenize()[0]

        self.assertEqual(
            str(token),
            "Keyword (class) - Line 1, Column 1",
        )

    def test_lexical_errors(self) -> None:
        invalid_sources = [
            '"unfinished string',
            "/* unfinished comment",
            "@",
            "12value",
            "3.14ff",
        ]

        for source in invalid_sources:
            with self.subTest(source=source):
                with self.assertRaises(LexicalError):
                    Lexer(source).tokenize()


if __name__ == "__main__":
    unittest.main()