"""Abstract Syntax Tree nodes for the Sea++ parser."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any


@dataclass
class ASTNode:
    """A generic and serializable AST node."""

    kind: str
    attributes: dict[str, Any] = field(default_factory=dict)
    children: list["ASTNode"] = field(default_factory=list)
    line: int | None = None
    column: int | None = None

    def add_child(self, node: "ASTNode | None") -> None:
        """Append a non-null child node."""

        if node is not None:
            self.children.append(node)

    def to_dict(self) -> dict[str, Any]:
        """Convert this node and all descendants to dictionaries."""

        result: dict[str, Any] = {"kind": self.kind}

        if self.attributes:
            result["attributes"] = self.attributes

        if self.line is not None:
            result["line"] = self.line

        if self.column is not None:
            result["column"] = self.column

        if self.children:
            result["children"] = [child.to_dict() for child in self.children]

        return result

    def to_json(self, indent: int = 2) -> str:
        """Serialize the AST to JSON text."""

        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            indent=indent,
        )

    def save_json(self, path: str | Path, indent: int = 2) -> None:
        """Save the AST as a JSON file."""

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self.to_json(indent=indent) + "\n",
            encoding="utf-8",
        )

    def pretty(self, level: int = 0) -> str:
        """Return a readable tree representation."""

        indent = "  " * level
        location = ""

        if self.line is not None and self.column is not None:
            location = f" [Line {self.line}, Column {self.column}]"

        attributes = ""

        if self.attributes:
            pairs = ", ".join(
                f"{key}={value!r}"
                for key, value in self.attributes.items()
            )
            attributes = f" ({pairs})"

        lines = [f"{indent}{self.kind}{attributes}{location}"]

        for child in self.children:
            lines.append(child.pretty(level + 1))

        return "\n".join(lines)

    @staticmethod
    def _escape_dot_text(value: Any) -> str:
        """Escape text so it can safely appear in a DOT label."""

        text = str(value)
        return (
            text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "")
        )

    def _graph_label(self) -> str:
        """Build the text displayed inside one graphical AST node."""

        label_lines = [self.kind]

        for key, value in self.attributes.items():
            label_lines.append(f"{key}: {value}")

        if self.line is not None and self.column is not None:
            label_lines.append(f"Line {self.line}, Column {self.column}")

        return "\\n".join(
            self._escape_dot_text(line)
            for line in label_lines
        )

    def _graph_style(self) -> tuple[str, str]:
        """Return the shape and fill color of an AST node."""

        declaration_nodes = {
            "Program",
            "ClassDeclaration",
            "FunctionDeclaration",
            "Parameter",
            "VariableDeclaration",
        }

        control_nodes = {
            "IfStatement",
            "IfBranch",
            "ElseIfBranch",
            "ElseBranch",
            "WhileStatement",
            "ForStatement",
            "ForInitializer",
            "ForCondition",
            "ForUpdate",
            "ReturnStatement",
            "Block",
        }

        expression_nodes = {
            "BinaryExpression",
            "UnaryExpression",
            "TernaryExpression",
            "AssignmentStatement",
            "UpdateExpression",
            "FunctionCall",
            "MemberAccess",
            "GroupedExpression",
        }

        leaf_nodes = {
            "Identifier",
            "Literal",
            "EmptyStatement",
            "UnknownExpression",
        }

        if self.kind == "Program":
            return "oval", "#B3E5FC"

        if self.kind in declaration_nodes:
            return "box", "#C8E6C9"

        if self.kind in control_nodes:
            return "box", "#FFE0B2"

        if self.kind in expression_nodes:
            return "ellipse", "#D1C4E9"

        if self.kind in leaf_nodes:
            return "ellipse", "#ECEFF1"

        return "box", "#FFFFFF"

    def to_dot(self) -> str:
        """Convert the complete AST to Graphviz DOT source."""

        lines = [
            "digraph SeaPlusPlusAST {",
            (
                '  graph [rankdir=TB, bgcolor="white", pad="0.3", '
                'nodesep="0.35", ranksep="0.55", splines=polyline];'
            ),
            (
                '  node [style="rounded,filled", fontname="Segoe UI", '
                'fontsize="10", color="#455A64", penwidth="1.1", '
                'margin="0.12,0.08"];'
            ),
            (
                '  edge [color="#546E7A", penwidth="1.0", '
                'arrowsize="0.7"];'
            ),
        ]

        next_id = 0

        def visit(node: "ASTNode", parent_id: str | None = None) -> None:
            nonlocal next_id

            node_id = f"node_{next_id}"
            next_id += 1

            shape, fill_color = node._graph_style()
            label = node._graph_label()

            lines.append(
                f'  {node_id} [label="{label}", shape={shape}, '
                f'fillcolor="{fill_color}"];'
            )

            if parent_id is not None:
                lines.append(f"  {parent_id} -> {node_id};")

            for child in node.children:
                visit(child, node_id)

        visit(self)
        lines.append("}")

        return "\n".join(lines) + "\n"

    def save_dot(self, path: str | Path) -> Path:
        """Save the AST in Graphviz DOT format."""

        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.to_dot(), encoding="utf-8")
        return output_path

    def render_graph(self, path: str | Path) -> tuple[Path, Path]:
        """Render the AST as PNG, SVG, or PDF using Graphviz."""

        output_path = Path(path)
        output_format = output_path.suffix.lower().lstrip(".")

        if output_format not in {"png", "svg", "pdf"}:
            raise ValueError(
                "AST graph output must use .png, .svg, or .pdf."
            )

        dot_executable = shutil.which("dot")

        if dot_executable is None:
            raise RuntimeError(
                "Graphviz was not found. Install Graphviz, restart the "
                "terminal, and verify it with: dot -V"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        dot_path = output_path.with_suffix(".dot")
        self.save_dot(dot_path)

        completed_process = subprocess.run(
            [
                dot_executable,
                f"-T{output_format}",
                str(dot_path),
                "-o",
                str(output_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        if completed_process.returncode != 0:
            error_message = completed_process.stderr.strip()
            raise RuntimeError(
                "Graphviz could not render the AST. " + error_message
            )

        return output_path, dot_path
