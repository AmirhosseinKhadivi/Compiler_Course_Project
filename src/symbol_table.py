"""Symbol information used by the Sea++ parser."""

from dataclasses import dataclass
from typing import Any


@dataclass
class VariableInfo:
    """Information about one declared variable."""

    type_name: str
    value: Any = None


@dataclass(frozen=True)
class ParameterInfo:
    """Information about one function parameter."""

    type_name: str
    name: str


@dataclass(frozen=True)
class FunctionInfo:
    """Information about one declared function."""

    return_type: str
    name: str
    parameters: tuple[ParameterInfo, ...]


class SymbolTable:
    """Store classes, functions, variables, and nested scopes."""

    def __init__(self) -> None:
        self.scopes: list[dict[str, VariableInfo]] = [{}]
        self.functions: dict[str, FunctionInfo] = {}
        self.classes: set[str] = set()

    def push_scope(self) -> None:
        """Create a new nested scope."""

        self.scopes.append({})

    def pop_scope(self) -> None:
        """Remove the current scope."""

        if len(self.scopes) == 1:
            raise RuntimeError(
                "Cannot remove the global scope."
            )

        self.scopes.pop()

    def declare_variable(
        self,
        name: str,
        type_name: str,
        value: Any = None,
    ) -> None:
        """Declare a variable in the current scope."""

        current_scope = self.scopes[-1]

        if name in current_scope:
            raise ValueError(
                f"Variable '{name}' is already defined "
                "in this scope."
            )

        current_scope[name] = VariableInfo(
            type_name=type_name,
            value=value,
        )

    def lookup_variable(
        self,
        name: str,
    ) -> VariableInfo | None:
        """Search for a variable from inner to outer scopes."""

        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]

        return None

    def assign_variable(
        self,
        name: str,
        value: Any,
    ) -> None:
        """Change the stored value of an existing variable."""

        for scope in reversed(self.scopes):
            if name in scope:
                scope[name].value = value
                return

    def declare_function(
        self,
        info: FunctionInfo,
        qualified_name: str | None = None,
    ) -> None:
        """Declare a function or class method."""

        key = qualified_name or info.name

        if key in self.functions:
            raise ValueError(
                f"Function '{info.name}' is already defined "
                "in this scope."
            )

        self.functions[key] = info

    def declare_class(self, name: str) -> None:
        """Declare a class."""

        if name in self.classes:
            raise ValueError(
                f"Class '{name}' is already defined."
            )

        self.classes.add(name)