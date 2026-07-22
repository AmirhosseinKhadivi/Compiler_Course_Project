"""
Command-line entry point for the Sea++ Phase 1 lexical analyzer.
"""

import argparse
import sys
from pathlib import Path

from src.lexer import Lexer, LexicalError


def build_argument_parser() -> argparse.ArgumentParser:
    """Create command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Scan a Sea++ source file and print its tokens."
        )
    )

    parser.add_argument(
        "source_file",
        type=Path,
        help="Path to the input Sea++ source file.",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional path for saving the token output.",
    )

    return parser


def read_source_file(source_path: Path) -> str:
    """Read a Sea++ source file using UTF-8 encoding."""

    if not source_path.exists():
        raise FileNotFoundError(
            f"Input file was not found: {source_path}"
        )

    if not source_path.is_file():
        raise IsADirectoryError(
            f"Input path is not a file: {source_path}"
        )

    return source_path.read_text(
        encoding="utf-8-sig"
    )


def format_tokens(source: str) -> str:
    """Run the lexer and format all tokens."""

    tokens = Lexer(source).tokenize()

    return "\n".join(
        str(token)
        for token in tokens
    )


def save_output(
    output_path: Path,
    content: str,
) -> None:
    """Save token output in a text file."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        content + ("\n" if content else ""),
        encoding="utf-8",
    )


def main() -> int:
    """Execute the lexical analyzer."""

    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        source = read_source_file(
            arguments.source_file
        )

        output = format_tokens(source)

        if output:
            print(output)

        if arguments.output is not None:
            save_output(
                arguments.output,
                output,
            )

            print(
                f"Token output saved to: {arguments.output}",
                file=sys.stderr,
            )

        return 0

    except (
        OSError,
        UnicodeError,
        LexicalError,
    ) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())