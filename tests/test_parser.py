"""Automated tests for the Sea++ Phase 2 parser."""

import unittest

from src.lexer import Lexer
from src.parser import Parser, ParseError


def parse_source(source: str) -> list[str]:
    """Run both lexer and parser."""

    tokens = Lexer(source).tokenize()

    return Parser(tokens).parse()


class ParserTests(unittest.TestCase):
    """Tests for the required Phase 2 features."""

    def test_complete_program_outputs(self) -> None:
        source = """
class MyClass begin
 int value = 10;

 void set_value(int x) begin
  value = x;
 end
end

void free_function(int a, int b) begin
end

void main() begin
 int j = 20 + 2 * 3 - 10 + 15 / 5;

 free_function(5, 10);

 for(int i = 0; i < 10; i++)
  free_function(i, j);

 while(j > 0)
  j--;

 if(j < 5)
  print("if");
 else if(j == 5)
  print("else if");
 else
  print("else");
end
"""

        output = parse_source(source)

        expected_parts = [
            "Class: MyClass",
            "Variable: int value = 10",
            "Function: void set_value(int x)",
            "Function: void free_function(int a, int b)",
            "Function: void main()",
            (
                "Variable: int j = "
                "20 + 2 * 3 - 10 + 15 / 5"
            ),
            "Math Expression Result: 19",
            "Call: free_function(5, 10)",
            "Loop: for",
            "Variable: int i = 0",
            "Call: free_function(i, j)",
            "Loop: while",
            "Conditional: if",
            'Call: print("if")',
            "Conditional: else if",
            'Call: print("else if")',
            "Conditional: else",
            'Call: print("else")',
        ]

        for expected_item in expected_parts:
            self.assertIn(
                expected_item,
                output,
            )

    def test_exactly_one_main_required(self) -> None:
        with self.assertRaises(ParseError):
            parse_source(
                "void helper() begin end"
            )

        with self.assertRaises(ParseError):
            parse_source(
                "void main() begin end "
                "int main() begin return 0; end"
            )

    def test_main_cannot_have_parameters(self) -> None:
        with self.assertRaises(ParseError):
            parse_source(
                "void main(int x) begin end"
            )

    def test_main_return_type(self) -> None:
        with self.assertRaises(ParseError):
            parse_source(
                "float main() begin end"
            )

    def test_single_statement_body_without_begin_end(
        self,
    ) -> None:
        source = """
void main() begin
 int x = 0;

 if(x == 0)
  x = 1;

 while(x < 3)
  x++;
end
"""

        output = parse_source(source)

        self.assertIn(
            "Conditional: if",
            output,
        )

        self.assertIn(
            "Loop: while",
            output,
        )

    def test_duplicate_variable_same_scope(self) -> None:
        source = """
void main() begin
 int x;
 int x;
end
"""

        with self.assertRaises(ParseError):
            parse_source(source)

    def test_member_function_call(self) -> None:
        source = """
class A begin
 void run(int x) begin
 end
end

void main() begin
 A object;
 object.run(10);
end
"""

        output = parse_source(source)

        self.assertIn(
            "Call: object.run(10)",
            output,
        )

    def test_ternary_expression(self) -> None:
        source = """
void main() begin
 int x = true ? 10 : 20;
end
"""

        output = parse_source(source)

        self.assertIn(
            "Variable: int x = true ? 10 : 20",
            output,
        )

    def test_syntax_error_has_position(self) -> None:
        with self.assertRaisesRegex(
            ParseError,
            r"Line 1, Column",
        ):
            parse_source(
                "void main( begin end"
            )


class ParserBonusTests(unittest.TestCase):
    """Tests for the optional Phase 2 features."""

    def build_parser(self, source: str) -> Parser:
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        parser.parse()
        return parser

    def test_ast_is_created(self) -> None:
        parser = self.build_parser(
            "void main() begin int x = 2 + 3 * 4; end"
        )

        ast_data = parser.ast.to_dict()

        self.assertEqual(ast_data["kind"], "Program")
        self.assertEqual(
            ast_data["children"][0]["kind"],
            "FunctionDeclaration",
        )
        self.assertIn(
            "BinaryExpression",
            parser.ast.pretty(),
        )

    def test_duplicate_class_is_rejected(self) -> None:
        source = """
class A begin end
class A begin end
void main() begin end
"""

        with self.assertRaisesRegex(
            ParseError,
            "Class 'A' is already defined",
        ):
            parse_source(source)

    def test_duplicate_function_is_rejected(self) -> None:
        source = """
void helper() begin end
void helper() begin end
void main() begin end
"""

        with self.assertRaisesRegex(
            ParseError,
            "Function 'helper' is already defined",
        ):
            parse_source(source)

    def test_forward_function_call_is_valid(self) -> None:
        source = """
void main() begin
 helper(10);
end

void helper(int value) begin
end
"""

        output = parse_source(source)
        self.assertIn("Call: helper(10)", output)

    def test_unknown_function_is_rejected(self) -> None:
        source = """
void main() begin
 missing(10);
end
"""

        with self.assertRaisesRegex(
            ParseError,
            "Function 'missing' is not defined",
        ):
            parse_source(source)

    def test_argument_count_is_checked(self) -> None:
        source = """
void helper(int value) begin end
void main() begin
 helper();
end
"""

        with self.assertRaisesRegex(
            ParseError,
            "expects 1 argument",
        ):
            parse_source(source)

    def test_argument_type_is_checked(self) -> None:
        source = """
void helper(int value) begin end
void main() begin
 helper("wrong");
end
"""

        with self.assertRaisesRegex(
            ParseError,
            "has type 'string'",
        ):
            parse_source(source)

    def test_member_function_call_is_validated(self) -> None:
        source = """
class A begin
 void run(int value) begin end
end

void main() begin
 A object;
 object.run(10);
end
"""

        output = parse_source(source)
        self.assertIn("Call: object.run(10)", output)

    def test_cyclic_dependency_warning(self) -> None:
        source = """
class A begin
 B b;
end

class B begin
 A a;
end

void main() begin end
"""

        output = parse_source(source)

        self.assertTrue(
            any(
                line.startswith(
                    "Warning: Cyclic dependency detected"
                )
                for line in output
            )
        )


if __name__ == "__main__":
    unittest.main()