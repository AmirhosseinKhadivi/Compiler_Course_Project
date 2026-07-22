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
            "Parse a Sea++ source file "
            "and print parser actions."
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
        help="Optional output text file.",
    )

    arguments = argument_parser.parse_args()

    try:
        source = arguments.source_file.read_text(
            encoding="utf-8-sig"
        )

        tokens = Lexer(source).tokenize()

        output_lines = Parser(tokens).parse()

        output = "\n".join(output_lines)

        if output:
            print(output)

        if arguments.output is not None:
            arguments.output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            arguments.output.write_text(
                output + ("\n" if output else ""),
                encoding="utf-8",
            )

            print(
                f"Parser output saved to: "
                f"{arguments.output}",
                file=sys.stderr,
            )

        return 0

    except (
        OSError,
        UnicodeError,
        LexicalError,
        ParseError,
    ) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())