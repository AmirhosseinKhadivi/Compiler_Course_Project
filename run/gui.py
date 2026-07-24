"""Graphical interface for the Sea++ compiler project."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk

from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from run.common import (  # noqa: E402
    OUTPUT_DIRECTORY,
    analyze_source,
    safe_base_name,
)


class SeaCompilerGUI:
    """GUI runner for Phase 1 and Phase 2."""

    PHASE_1_TEXT = "Phase 1 - Lexer Only"
    PHASE_2_TEXT = "Phase 2 - Full Analysis"

    def __init__(
        self,
        root: tk.Tk,
    ) -> None:
        self.root = root

        self.root.title(
            "Sea++ Compiler"
        )

        self.root.geometry(
            "1220x780"
        )

        self.root.minsize(
            920,
            620,
        )

        self.source_path: Path | None = None
        self.last_ast_image: Path | None = None

        self.phase_mode = tk.StringVar(
            value=self.PHASE_2_TEXT
        )

        self.input_path_text = tk.StringVar(
            value="Manual input"
        )

        self.output_path_text = tk.StringVar(
            value=str(OUTPUT_DIRECTORY)
        )

        self.status_text = tk.StringVar(
            value="Ready"
        )

        self._configure_style()
        self._build_interface()

    def _configure_style(self) -> None:
        """Configure GUI appearance."""

        style = ttk.Style()

        try:
            style.theme_use(
                "vista"
            )
        except tk.TclError:
            pass

        style.configure(
            "Title.TLabel",
            font=(
                "Segoe UI",
                18,
                "bold",
            ),
        )

        style.configure(
            "Primary.TButton",
            font=(
                "Segoe UI",
                10,
                "bold",
            ),
            padding=(
                18,
                8,
            ),
        )

    def _build_interface(self) -> None:
        """Build all interface controls."""

        main_frame = ttk.Frame(
            self.root,
            padding=12,
        )

        main_frame.pack(
            fill=tk.BOTH,
            expand=True,
        )

        # -----------------------------------------------------
        # Header
        # -----------------------------------------------------

        header_frame = ttk.Frame(
            main_frame
        )

        header_frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        ttk.Label(
            header_frame,
            text="Sea++ Compiler",
            style="Title.TLabel",
        ).pack(
            side=tk.LEFT,
        )

        ttk.Label(
            header_frame,
            text=(
                "Lexer | Parser | Semantic Checks | AST"
            ),
        ).pack(
            side=tk.LEFT,
            padx=(18, 0),
            pady=(8, 0),
        )

        # -----------------------------------------------------
        # Toolbar
        # -----------------------------------------------------

        toolbar = ttk.Frame(
            main_frame
        )

        toolbar.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        ttk.Button(
            toolbar,
            text="Open Input File",
            command=self.open_input_file,
        ).pack(
            side=tk.LEFT,
            padx=(0, 5),
        )

        ttk.Button(
            toolbar,
            text="New Input",
            command=self.new_input,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Button(
            toolbar,
            text="Save Input",
            command=self.save_input,
        ).pack(
            side=tk.LEFT,
            padx=5,
        )

        ttk.Label(
            toolbar,
            text="Mode:",
        ).pack(
            side=tk.LEFT,
            padx=(18, 6),
        )

        self.phase_combobox = ttk.Combobox(
            toolbar,
            textvariable=self.phase_mode,
            values=[
                self.PHASE_1_TEXT,
                self.PHASE_2_TEXT,
            ],
            state="readonly",
            width=25,
        )

        self.phase_combobox.pack(
            side=tk.LEFT,
        )

        ttk.Button(
            toolbar,
            text="Analyze",
            command=self.analyze,
            style="Primary.TButton",
        ).pack(
            side=tk.RIGHT,
        )

        # -----------------------------------------------------
        # Paths
        # -----------------------------------------------------

        information_frame = ttk.Frame(
            main_frame
        )

        information_frame.pack(
            fill=tk.X,
            pady=(0, 10),
        )

        ttk.Label(
            information_frame,
            text="Input:",
        ).grid(
            row=0,
            column=0,
            sticky=tk.W,
        )

        ttk.Label(
            information_frame,
            textvariable=self.input_path_text,
        ).grid(
            row=0,
            column=1,
            sticky=tk.W,
            padx=(8, 0),
        )

        ttk.Label(
            information_frame,
            text="Output:",
        ).grid(
            row=1,
            column=0,
            sticky=tk.W,
            pady=(4, 0),
        )

        ttk.Label(
            information_frame,
            textvariable=self.output_path_text,
        ).grid(
            row=1,
            column=1,
            sticky=tk.W,
            padx=(8, 0),
            pady=(4, 0),
        )

        information_frame.columnconfigure(
            1,
            weight=1,
        )

        # -----------------------------------------------------
        # Source and result panels
        # -----------------------------------------------------

        panels = ttk.PanedWindow(
            main_frame,
            orient=tk.HORIZONTAL,
        )

        panels.pack(
            fill=tk.BOTH,
            expand=True,
        )

        source_frame = ttk.LabelFrame(
            panels,
            text="Sea++ Source Code",
            padding=8,
        )

        result_frame = ttk.LabelFrame(
            panels,
            text="Analysis Result",
            padding=8,
        )

        panels.add(
            source_frame,
            weight=1,
        )

        panels.add(
            result_frame,
            weight=1,
        )

        # -----------------------------------------------------
        # Source editor
        # -----------------------------------------------------

        self.source_text = tk.Text(
            source_frame,
            wrap=tk.NONE,
            undo=True,
            font=(
                "Consolas",
                11,
            ),
        )

        source_vertical_scrollbar = ttk.Scrollbar(
            source_frame,
            orient=tk.VERTICAL,
            command=self.source_text.yview,
        )

        source_horizontal_scrollbar = ttk.Scrollbar(
            source_frame,
            orient=tk.HORIZONTAL,
            command=self.source_text.xview,
        )

        self.source_text.configure(
            yscrollcommand=(
                source_vertical_scrollbar.set
            ),
            xscrollcommand=(
                source_horizontal_scrollbar.set
            ),
        )

        self.source_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        source_vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        source_horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        source_frame.rowconfigure(
            0,
            weight=1,
        )

        source_frame.columnconfigure(
            0,
            weight=1,
        )

        # -----------------------------------------------------
        # Result panel
        # -----------------------------------------------------

        self.result_text = tk.Text(
            result_frame,
            wrap=tk.NONE,
            state=tk.DISABLED,
            font=(
                "Consolas",
                10,
            ),
        )

        result_vertical_scrollbar = ttk.Scrollbar(
            result_frame,
            orient=tk.VERTICAL,
            command=self.result_text.yview,
        )

        result_horizontal_scrollbar = ttk.Scrollbar(
            result_frame,
            orient=tk.HORIZONTAL,
            command=self.result_text.xview,
        )

        self.result_text.configure(
            yscrollcommand=(
                result_vertical_scrollbar.set
            ),
            xscrollcommand=(
                result_horizontal_scrollbar.set
            ),
        )

        self.result_text.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="nsew",
        )

        result_vertical_scrollbar.grid(
            row=0,
            column=3,
            sticky="ns",
        )

        result_horizontal_scrollbar.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
        )

        ttk.Button(
            result_frame,
            text="Open AST Image",
            command=self.open_ast_image,
        ).grid(
            row=2,
            column=0,
            sticky=tk.W,
            pady=(8, 0),
        )

        ttk.Button(
            result_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
        ).grid(
            row=2,
            column=1,
            pady=(8, 0),
        )

        ttk.Button(
            result_frame,
            text="Clear Result",
            command=self.clear_result,
        ).grid(
            row=2,
            column=2,
            sticky=tk.E,
            pady=(8, 0),
        )

        result_frame.rowconfigure(
            0,
            weight=1,
        )

        for column_index in range(3):
            result_frame.columnconfigure(
                column_index,
                weight=1,
            )

        # -----------------------------------------------------
        # Status
        # -----------------------------------------------------

        ttk.Separator(
            main_frame,
            orient=tk.HORIZONTAL,
        ).pack(
            fill=tk.X,
            pady=(8, 5),
        )

        ttk.Label(
            main_frame,
            textvariable=self.status_text,
        ).pack(
            anchor=tk.W,
        )

    def open_input_file(self) -> None:
        """Load a source file using a file picker."""

        samples_directory = (
            PROJECT_ROOT
            / "samples"
        )

        if samples_directory.exists():
            initial_directory = (
                samples_directory
            )
        else:
            initial_directory = (
                PROJECT_ROOT
            )

        selected_file = (
            filedialog.askopenfilename(
                title=(
                    "Select Sea++ input file"
                ),
                initialdir=str(
                    initial_directory
                ),
                filetypes=[
                    (
                        "Sea++ source files",
                        "*.sea",
                    ),
                    (
                        "Text files",
                        "*.txt",
                    ),
                    (
                        "All files",
                        "*.*",
                    ),
                ],
            )
        )

        if not selected_file:
            return

        source_path = Path(
            selected_file
        )

        try:
            source_code = (
                source_path.read_text(
                    encoding="utf-8-sig",
                )
            )

        except (
            OSError,
            UnicodeError,
        ) as error:
            messagebox.showerror(
                "Open Error",
                str(error),
            )
            return

        self.source_text.delete(
            "1.0",
            tk.END,
        )

        self.source_text.insert(
            "1.0",
            source_code,
        )

        self.source_path = source_path
        self.last_ast_image = None

        self.input_path_text.set(
            str(source_path)
        )

        self.status_text.set(
            f"Loaded: {source_path.name}"
        )

    def new_input(self) -> None:
        """Clear current source and create manual input."""

        current_source = (
            self.source_text.get(
                "1.0",
                "end-1c",
            )
        )

        if current_source.strip():
            should_clear = (
                messagebox.askyesno(
                    "New Input",
                    (
                        "Clear the current "
                        "source code?"
                    ),
                )
            )

            if not should_clear:
                return

        self.source_text.delete(
            "1.0",
            tk.END,
        )

        self.source_path = None
        self.last_ast_image = None

        self.input_path_text.set(
            "Manual input"
        )

        self.clear_result()

        self.status_text.set(
            "New input created"
        )

    def save_input(self) -> None:
        """Save editor contents in a Sea++ file."""

        source_code = (
            self.source_text.get(
                "1.0",
                "end-1c",
            )
        )

        if self.source_path is None:
            samples_directory = (
                PROJECT_ROOT
                / "samples"
            )

            samples_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            selected_file = (
                filedialog.asksaveasfilename(
                    title=(
                        "Save Sea++ input"
                    ),
                    initialdir=str(
                        samples_directory
                    ),
                    defaultextension=".sea",
                    filetypes=[
                        (
                            "Sea++ source files",
                            "*.sea",
                        ),
                        (
                            "Text files",
                            "*.txt",
                        ),
                    ],
                )
            )

            if not selected_file:
                return

            self.source_path = Path(
                selected_file
            )

        try:
            self.source_path.write_text(
                source_code,
                encoding="utf-8",
            )

        except (
            OSError,
            UnicodeError,
        ) as error:
            messagebox.showerror(
                "Save Error",
                str(error),
            )
            return

        self.input_path_text.set(
            str(self.source_path)
        )

        self.status_text.set(
            f"Saved: {self.source_path.name}"
        )

    def analyze(self) -> None:
        """Run selected compiler phase."""

        source_code = (
            self.source_text.get(
                "1.0",
                "end-1c",
            )
        )

        if not source_code.strip():
            messagebox.showwarning(
                "Empty Input",
                (
                    "Open a Sea++ file or type "
                    "source code first."
                ),
            )
            return

        if (
            self.phase_mode.get()
            == self.PHASE_1_TEXT
        ):
            phase = 1
        else:
            phase = 2

        if self.source_path is not None:
            base_name = (
                self.source_path.stem
            )
        else:
            base_name = (
                "manual_input"
            )

        self.status_text.set(
            "Analyzing..."
        )

        self.root.update_idletasks()

        try:
            result = analyze_source(
                source_code=source_code,
                base_name=base_name,
                phase=phase,
            )

            if phase == 1:
                result_title = (
                    "PHASE 1 LEXICAL "
                    "ANALYSIS COMPLETED"
                )

                analysis_output = (
                    result.token_text
                )

            else:
                result_title = (
                    "PHASE 2 FULL "
                    "ANALYSIS COMPLETED"
                )

                analysis_output = (
                    result.parser_text
                )

            result_lines = [
                result_title,
                "=" * 72,
                "",
                "ANALYSIS OUTPUT",
                "-" * 72,
                (
                    analysis_output
                    if analysis_output
                    else (
                        "No output messages "
                        "were generated."
                    )
                ),
                "",
                "GENERATED FILES",
                "-" * 72,
            ]

            for (
                file_name,
                file_path,
            ) in result.generated_files.items():
                result_lines.append(
                    f"{file_name}: {file_path}"
                )

            if result.warnings:
                result_lines.extend(
                    [
                        "",
                        "WARNINGS",
                        "-" * 72,
                    ]
                )

                result_lines.extend(
                    result.warnings
                )

            self.show_result(
                "\n".join(
                    result_lines
                )
            )

            self.last_ast_image = (
                result.generated_files.get(
                    "ast_image"
                )
            )

            self.status_text.set(
                (
                    f"Phase {phase} "
                    "completed successfully"
                )
            )

            messagebox.showinfo(
                "Analysis Complete",
                (
                    f"Phase {phase} "
                    "completed successfully.\n\n"
                    "Generated files were "
                    "saved only in:\n"
                    f"{OUTPUT_DIRECTORY}"
                ),
            )

        except Exception as error:
            self.last_ast_image = None

            error_text = (
                f"{type(error).__name__}: "
                f"{error}"
            )

            self.show_result(
                "ANALYSIS FAILED\n"
                + "=" * 72
                + "\n\n"
                + error_text
            )

            self.status_text.set(
                "Analysis failed"
            )

            error_path = (
                self.save_error(
                    base_name=base_name,
                    error_text=error_text,
                )
            )

            messagebox.showerror(
                "Compiler Error",
                (
                    f"{error}\n\n"
                    "Error report saved in:\n"
                    f"{error_path}"
                ),
            )

    @staticmethod
    def save_error(
        base_name: str,
        error_text: str,
    ) -> Path:
        """Save errors only inside the output folder."""

        OUTPUT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        timestamp = (
            datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
        )

        error_path = (
            OUTPUT_DIRECTORY
            / (
                f"{safe_base_name(base_name)}"
                f"_error_{timestamp}.txt"
            )
        )

        error_path.write_text(
            error_text + "\n",
            encoding="utf-8",
        )

        return error_path

    def show_result(
        self,
        text: str,
    ) -> None:
        """Show result text."""

        self.result_text.configure(
            state=tk.NORMAL,
        )

        self.result_text.delete(
            "1.0",
            tk.END,
        )

        self.result_text.insert(
            "1.0",
            text,
        )

        self.result_text.configure(
            state=tk.DISABLED,
        )

    def clear_result(self) -> None:
        """Clear result panel."""

        self.show_result("")

    def open_ast_image(self) -> None:
        """Open latest generated AST image."""

        if (
            self.last_ast_image is None
            or not self.last_ast_image.exists()
        ):
            messagebox.showwarning(
                "AST Image",
                (
                    "No AST image is available.\n\n"
                    "The graphical AST is generated "
                    "only after a successful Phase 2 run."
                ),
            )
            return

        self.open_path(
            self.last_ast_image
        )

    def open_output_folder(self) -> None:
        """Open the fixed output folder."""

        OUTPUT_DIRECTORY.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.open_path(
            OUTPUT_DIRECTORY
        )

    @staticmethod
    def open_path(
        path: Path,
    ) -> None:
        """Open a file or folder with the operating system."""

        resolved_path = path.resolve()

        if os.name == "nt":
            os.startfile(
                str(resolved_path)
            )
            return

        if sys.platform == "darwin":
            subprocess.Popen(
                [
                    "open",
                    str(resolved_path),
                ]
            )
            return

        subprocess.Popen(
            [
                "xdg-open",
                str(resolved_path),
            ]
        )


def main() -> None:
    """Launch the Sea++ compiler GUI."""

    root = tk.Tk()

    SeaCompilerGUI(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()