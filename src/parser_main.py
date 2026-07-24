"""Command-line entry point for the Sea++ Phase 2 parser."""

import argparse
import sys
from pathlib import Path

from src.lexer import Lexer, LexicalError
from src.parser import Parser, ParseError


def main() -> int:
    """Run the lexer and parser on a Sea++ source file."""

    argument_parser = argparse.ArgumentParser(
        description=(
            "Parse a Sea++ source file, print parser actions, "
            "and optionally save the generated AST."
        )
    )

    argument_parser.add_argument(
        "source_file",
        type=Path,
        help="Path to the Sea++ input file.",
    )

    argument_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional parser output text file.",
    )

    argument_parser.add_argument(
        "--ast-output",
        type=Path,
        help="Optional JSON file for the generated AST.",
    )

    argument_parser.add_argument(
        "--ast-tree-output",
        type=Path,
        help="Optional readable text file for the generated AST tree.",
    )

    argument_parser.add_argument(
        "--ast-image-output",
        type=Path,
        help=(
            "Optional graphical AST output. The extension must be "
            ".png, .svg, or .pdf. Graphviz must be installed."
        ),
    )

    arguments = argument_parser.parse_args()

    try:
        source = arguments.source_file.read_text(encoding="utf-8-sig")
        tokens = Lexer(source).tokenize()
        parser = Parser(tokens)
        output_lines = parser.parse()
        output = "\n".join(output_lines)

        if output:
            print(output)

        if arguments.output is not None:
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(
                output + ("\n" if output else ""),
                encoding="utf-8",
            )
            print(
                f"Parser output saved to: {arguments.output}",
                file=sys.stderr,
            )

        if arguments.ast_output is not None:
            parser.ast.save_json(arguments.ast_output)
            print(
                f"AST JSON saved to: {arguments.ast_output}",
                file=sys.stderr,
            )

        if arguments.ast_tree_output is not None:
            arguments.ast_tree_output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            arguments.ast_tree_output.write_text(
                parser.ast.pretty() + "\n",
                encoding="utf-8",
            )
            print(
                f"AST tree saved to: {arguments.ast_tree_output}",
                file=sys.stderr,
            )

        if arguments.ast_image_output is not None:
            image_path, dot_path = parser.ast.render_graph(
                arguments.ast_image_output
            )
            print(
                f"Graphical AST saved to: {image_path}",
                file=sys.stderr,
            )
            print(
                f"Graphviz DOT source saved to: {dot_path}",
                file=sys.stderr,
            )

        return 0

    except (
        OSError,
        UnicodeError,
        ValueError,
        RuntimeError,
        LexicalError,
        ParseError,
    ) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())