"""Run the complete Sea++ compiler project using one input path."""

from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from src.lexer import Lexer, LexicalError
from src.parser import Parser, ParseError


# ============================================================
# Only change this path when you want to analyze another file.
# You can use either an absolute path or a project-relative path.
# ============================================================

INPUT_FILE = r"samples\phase2_bonus_test.sea"


# Automatically open the generated AST image after analysis.
OPEN_AST_IMAGE = True

# Automatically open the output folder after analysis.
OPEN_OUTPUT_FOLDER = False


PROJECT_DIRECTORY = Path(__file__).resolve().parent
OUTPUT_DIRECTORY = PROJECT_DIRECTORY / "output"


def resolve_input_path(input_path: str) -> Path:
    """Convert the configured input path to an absolute path."""

    path = Path(input_path.strip().strip('"'))

    if not path.is_absolute():
        path = PROJECT_DIRECTORY / path

    return path.resolve()


def show_information(title: str, message: str) -> None:
    """Show a Windows information dialog."""

    root = tk.Tk()
    root.withdraw()

    messagebox.showinfo(
        title,
        message,
        parent=root,
    )

    root.destroy()


def show_error(title: str, message: str) -> None:
    """Show a Windows error dialog."""

    root = tk.Tk()
    root.withdraw()

    messagebox.showerror(
        title,
        message,
        parent=root,
    )

    root.destroy()


def open_path(path: Path) -> None:
    """Open a file or folder with the default Windows application."""

    if os.name == "nt":
        os.startfile(str(path.resolve()))


def save_tokens(
    tokens: list,
    output_path: Path,
) -> None:
    """Save lexer tokens to a text file."""

    token_text = "\n".join(
        str(token)
        for token in tokens
    )

    output_path.write_text(
        token_text + ("\n" if token_text else ""),
        encoding="utf-8",
    )


def save_parser_output(
    output_lines: list[str],
    output_path: Path,
) -> None:
    """Save parser actions and semantic messages."""

    output_text = "\n".join(output_lines)

    output_path.write_text(
        output_text + ("\n" if output_text else ""),
        encoding="utf-8",
    )


def run_compiler() -> None:
    """Run lexer, parser, semantic checks, and AST generation."""

    input_path = resolve_input_path(INPUT_FILE)

    if not input_path.exists():
        raise FileNotFoundError(
            "Input file was not found:\n"
            f"{input_path}"
        )

    if not input_path.is_file():
        raise ValueError(
            "The configured input path is not a file:\n"
            f"{input_path}"
        )

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_code = input_path.read_text(
        encoding="utf-8-sig",
    )

    if not source_code.strip():
        raise ValueError(
            "The input file is empty."
        )

    base_name = input_path.stem

    tokens_output_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_tokens.txt"
    )

    parser_output_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_parser_output.txt"
    )

    ast_json_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_ast.json"
    )

    ast_tree_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_ast_tree.txt"
    )

    ast_image_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_ast.png"
    )

    error_output_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_error.txt"
    )

    # Phase 1: Lexical analysis
    lexer = Lexer(source_code)
    tokens = lexer.tokenize()

    # Phase 2: Parsing, semantic checks, and AST construction
    parser = Parser(tokens)
    parser_output_lines = parser.parse()

    # Save Phase 1 output
    save_tokens(
        tokens,
        tokens_output_path,
    )

    # Save Phase 2 output
    save_parser_output(
        parser_output_lines,
        parser_output_path,
    )

    # Save AST as JSON
    parser.ast.save_json(
        ast_json_path,
    )

    # Save AST as readable text
    ast_tree_path.write_text(
        parser.ast.pretty() + "\n",
        encoding="utf-8",
    )

    # Save graphical AST
    ast_image, ast_dot = parser.ast.render_graph(
        ast_image_path,
    )

    # Delete an old error file after a successful run.
    if error_output_path.exists():
        error_output_path.unlink()

    generated_files = [
        tokens_output_path,
        parser_output_path,
        ast_json_path,
        ast_tree_path,
        ast_dot,
        ast_image,
    ]

    result_message = (
        "Analysis completed successfully.\n\n"
        f"Input:\n{input_path}\n\n"
        "Generated files:\n"
        + "\n".join(
            str(path)
            for path in generated_files
        )
    )

    show_information(
        "Sea++ Compiler",
        result_message,
    )

    if OPEN_AST_IMAGE:
        open_path(ast_image)

    if OPEN_OUTPUT_FOLDER:
        open_path(OUTPUT_DIRECTORY)


def main() -> int:
    """Program entry point."""

    input_path = resolve_input_path(INPUT_FILE)
    base_name = input_path.stem or "compiler"

    error_output_path = (
        OUTPUT_DIRECTORY
        / f"{base_name}_error.txt"
    )

    try:
        run_compiler()
        return 0

    except (
        FileNotFoundError,
        OSError,
        UnicodeError,
        ValueError,
        RuntimeError,
        AttributeError,
        LexicalError,
        ParseError,
    ) as error:
        OUTPUT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        error_message = (
            f"{type(error).__name__}: {error}"
        )

        error_output_path.write_text(
            error_message + "\n",
            encoding="utf-8",
        )

        show_error(
            "Sea++ Compiler Error",
            error_message
            + "\n\n"
            + "The error was also saved in:\n"
            + str(error_output_path),
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())