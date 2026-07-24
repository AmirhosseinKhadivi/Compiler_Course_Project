"""Interactive terminal runner for the Sea++ compiler."""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from run.common import (  # noqa: E402
    OUTPUT_DIRECTORY,
    analyze_source,
)


def print_header() -> None:
    """Display the application header."""

    print()
    print("=" * 70)
    print("Sea++ Compiler")
    print("=" * 70)
    print()


def get_input_file() -> Path:
    """Ask the user to enter the source-file path."""

    while True:
        print("Enter the Sea++ source-file path.")
        print(
            "Example: samples\\phase1_sample.sea"
        )
        print()

        input_value = input(
            "Input file: "
        ).strip().strip('"')

        if not input_value:
            print()
            print(
                "Error: The input path cannot be empty."
            )
            print()
            continue

        input_path = Path(
            input_value
        ).expanduser()

        if not input_path.is_absolute():
            input_path = (
                PROJECT_ROOT
                / input_path
            )

        input_path = input_path.resolve()

        if not input_path.exists():
            print()
            print(
                "Error: The selected file does not exist."
            )
            print(
                f"Path: {input_path}"
            )
            print()
            continue

        if not input_path.is_file():
            print()
            print(
                "Error: The selected path is not a file."
            )
            print()
            continue

        return input_path


def get_phase() -> int:
    """Ask the user to select Phase 1 or Phase 2."""

    while True:
        print()
        print("Select compiler phase:")
        print()
        print(
            "1 - Phase 1: Lexer Only"
        )
        print(
            "2 - Phase 2: Full Analysis"
        )
        print()

        selected_phase = input(
            "Phase number: "
        ).strip()

        if selected_phase == "1":
            return 1

        if selected_phase == "2":
            return 2

        print()
        print(
            "Error: Enter only 1 or 2."
        )


def display_result(
    phase: int,
    input_path: Path,
    result,
) -> None:
    """Display generated outputs."""

    print()
    print("=" * 70)

    if phase == 1:
        print(
            "PHASE 1 LEXICAL ANALYSIS COMPLETED"
        )
    else:
        print(
            "PHASE 2 FULL ANALYSIS COMPLETED"
        )

    print("=" * 70)
    print()

    print(
        f"Input file: {input_path}"
    )

    print(
        f"Output folder: {OUTPUT_DIRECTORY}"
    )

    print()
    print("Generated files:")
    print("-" * 70)

    for (
        file_name,
        file_path,
    ) in result.generated_files.items():
        print(
            f"{file_name}: {file_path}"
        )

    if result.warnings:
        print()
        print("Warnings:")
        print("-" * 70)

        for warning in result.warnings:
            print(
                f"- {warning}"
            )

    print()


def run_again() -> bool:
    """Ask whether another input should be analyzed."""

    while True:
        answer = input(
            "Analyze another file? [y/n]: "
        ).strip().lower()

        if answer in {
            "y",
            "yes",
        }:
            return True

        if answer in {
            "n",
            "no",
        }:
            return False

        print(
            "Enter y or n."
        )


def main() -> None:
    """Run the interactive terminal application."""

    print_header()

    while True:
        try:
            input_path = get_input_file()

            phase = get_phase()

            source_code = input_path.read_text(
                encoding="utf-8-sig",
            )

            print()
            print(
                "Analyzing source code..."
            )
            print()

            result = analyze_source(
                source_code=source_code,
                base_name=input_path.stem,
                phase=phase,
            )

            display_result(
                phase=phase,
                input_path=input_path,
                result=result,
            )

        except Exception as error:
            print()
            print("=" * 70)
            print("ANALYSIS FAILED")
            print("=" * 70)
            print()

            print(
                f"{type(error).__name__}: {error}"
            )

            print()

        if not run_again():
            break

        print()
        print("-" * 70)
        print()

    print()
    print(
        "Sea++ Compiler closed."
    )
    print()


if __name__ == "__main__":
    main()