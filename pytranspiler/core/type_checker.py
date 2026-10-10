"""Type resolution pass.

Fills in the ``type`` attributes of IR nodes through local type
propagation and validates that the inferred types are consistent.  This is
what makes ``x = 10`` work without an explicit annotation: the integer
literal is typed ``i64`` and the assignment inherits it.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import ir
from .ir import NUMERIC_ORDER


class TypeCheckError(TypeError):
    """Raised when the IR is not well-typed."""


def _wider(a: str, b: str) -> str:
    """Return the wider of two numeric types."""
    return a if NUMERIC_ORDER[a] >= NUMERIC_ORDER[b] else b


class TypeChecker:
    def __init__(self, frontend_rules: Optional[Dict[str, Any]] = None):
        rules = frontend_rules or {}
        self.builtin_returns: Dict[str, str] = rules.get("builtin_return_types", {})

    # -- entry point --------------------------------------------------------

    def check(self, module_ir: Dict[str, Any]) -> Dict[str, Any]:
        ir.validate(module_ir)
        for fn in module_ir["body"]:
            if fn.get("node") == ir.FUNCTION_DEF:
                self._check_function(fn)
        return module_ir

    # -- functions ----------------------------------------------------------

    def _check_function(self, fn: Dict[str, Any]) -> None:
        env: Dict[str, Optional[str]] = {}
        for p in fn["params"]:
            env[p["name"]] = p["type"]

        # Count assignments per name so backends can tell a first declaration
        # (needs `let`) from a reassignment, and can decide whether a binding
        # must be mutable.
        counts: Dict[str, int] = {}
        self._count_assigns(fn["body"], counts)
        for p in fn["params"]:
            p["mutable"] = counts.get(p["name"], 0) >= 1

        return_types: List[str] = []
        self._check_block(fn["body"], env, return_types, counts)

        # Resolve return type.
        inferred = self._unify_returns(return_types)
        annotated = fn.get("return_type")
        if annotated is None:
            fn["return_type"] = inferred or "void"
        elif inferred not in (None, "void") and not self._assignable(annotated, inferred):
            raise TypeCheckError(
                f"function '{fn['name']}': annotated return type '{annotated}' "
                f"conflicts with inferred '{inferred}'"
            )
        elif inferred == "void" and annotated != "void":
            # A function that returns nothing but claims a type is an error.
            raise TypeCheckError(
                f"function '{fn['name']}': annotated '{annotated}' but no value is returned"
            )

        # Any parameter that is still untyped defaults to i64.
        for p in fn["params"]:
            if p["type"] is None:
                p["type"] = "i64"

    @staticmethod
    def _count_assigns(body: List[Dict[str, Any]], counts: Dict[str, int]) -> None:
        for stmt in body:
            kind = stmt.get("node")
            if kind == ir.ASSIGN:
                counts[stmt["target"]] = counts.get(stmt["target"], 0) + 1
            elif kind == ir.IF:
                TypeChecker._count_assigns(stmt["body"], counts)
                TypeChecker._count_assigns(stmt["orelse"], counts)
            elif kind == ir.WHILE:
                TypeChecker._count_assigns(stmt["body"], counts)

    def _check_block(
        self,
        body: List[Dict[str, Any]],
        env: Dict[str, Optional[str]],
        return_types: List[str],
        counts: Dict[str, int],
    ) -> None:
        for stmt in body:
            self._check_stmt(stmt, env, return_types, counts)

    def _check_stmt(
        self,
        stmt: Dict[str, Any],
        env: Dict[str, Optional[str]],
        return_types: List[str],
        counts: Dict[str, int],
    ) -> None:
        kind = stmt["node"]
        if kind == ir.RETURN:
            if stmt["value"] is None:
                return_types.append("void")
            else:
                return_types.append(self._infer(stmt["value"], env))
        elif kind == ir.ASSIGN:
            value_type = self._infer(stmt["value"], env)
            annotated = stmt.get("type")
            if annotated is not None and not self._assignable(annotated, value_type):
                raise TypeCheckError(
                    f"assignment to '{stmt['target']}': annotated '{annotated}' "
                    f"is incompatible with inferred '{value_type}'"
                )
            name = stmt["target"]
            stmt["decl"] = name not in env
            stmt["mutable"] = counts.get(name, 0) >= 2
            stmt["type"] = annotated or value_type or "i64"
            env[name] = stmt["type"]
        elif kind == ir.IF:
            self._require_bool(stmt["test"], env, "if condition")
            self._check_block(stmt["body"], env, return_types, counts)
            self._check_block(stmt["orelse"], env, return_types, counts)
        elif kind == ir.WHILE:
            self._require_bool(stmt["test"], env, "while condition")
            self._check_block(stmt["body"], env, return_types, counts)
        elif kind == ir.FUNCTION_DEF:
            raise TypeCheckError("nested function definitions are not supported")
        else:
            # Bare expression statement (e.g. print(...)).
            self._infer(stmt, env)

    # -- expressions --------------------------------------------------------

    def _infer(self, node: Dict[str, Any], env: Dict[str, Optional[str]]) -> Optional[str]:
        kind = node["node"]

        if kind == ir.LITERAL:
            if node.get("type") is None:
                node["type"] = self._literal_type(node["value"])
            return node["type"]

        if kind == ir.VAR:
            if node["name"] not in env:
                raise TypeCheckError(f"use of undefined variable '{node['name']}'")
            node["type"] = env[node["name"]] or node.get("type")
            return node["type"]

        if kind == ir.BIN_OP:
            lt = self._infer(node["left"], env)
            rt = self._infer(node["right"], env)
            result = self._binop_type(node["op"], lt, rt)
            node["type"] = result
            return result

        if kind == ir.UNARY_OP:
            ot = self._infer(node["operand"], env)
            node["type"] = "bool" if node["op"] == "NOT" else ot
            return node["type"]

        if kind == ir.COMPARE:
            lt = self._infer(node["left"], env)
            rt = self._infer(node["right"], env)
            if lt and rt and lt != rt and not self._both_numeric(lt, rt):
                raise TypeCheckError(f"cannot compare '{lt}' with '{rt}'")
            node["type"] = "bool"
            return "bool"

        if kind == ir.CALL:
            for i, arg in enumerate(node["args"]):
                self._infer(arg, env)
            if node["func"] not in self.builtin_returns:
                raise TypeCheckError(f"call to unknown function '{node['func']}'")
            node["type"] = self.builtin_returns[node["func"]]
            return node["type"]

        raise TypeCheckError(f"cannot infer type of node {kind!r}")

    def _require_bool(
        self, node: Dict[str, Any], env: Dict[str, Optional[str]], what: str
    ) -> None:
        t = self._infer(node, env)
        if t not in (None, "bool", "i64"):
            raise TypeCheckError(f"{what} must be boolean, got '{t}'")

    # -- type rules ---------------------------------------------------------

    def _binop_type(self, op: str, lt: Optional[str], rt: Optional[str]) -> str:
        if op in ("AND", "OR"):
            return "bool"
        if lt is None:
            return rt or "i64"
        if rt is None:
            return lt
        if op == "DIV":
            # Python true division always produces a float.
            return "f64"
        if lt == "str" and rt == "str":
            if op == "ADD":
                return "str"
            raise TypeCheckError(f"operator '{op}' is not defined for strings")
        if not self._both_numeric(lt, rt):
            raise TypeCheckError(f"operator '{op}' cannot combine '{lt}' and '{rt}'")
        return _wider(lt, rt)

    @staticmethod
    def _both_numeric(a: str, b: str) -> bool:
        return a in NUMERIC_ORDER and b in NUMERIC_ORDER

    @staticmethod
    def _assignable(target: str, source: Optional[str]) -> bool:
        if source is None:
            return True
        if target == source:
            return True
        if target in NUMERIC_ORDER and source in NUMERIC_ORDER:
            # Widening conversions are allowed (e.g. i64 -> f64).
            return NUMERIC_ORDER[target] >= NUMERIC_ORDER[source]
        return False

    @staticmethod
    def _unify_returns(types: List[str]) -> Optional[str]:
        concrete = [t for t in types if t not in (None, "void")]
        if not concrete:
            return "void" if types else None
        result = concrete[0]
        for t in concrete[1:]:
            if t == result:
                continue
            if t in NUMERIC_ORDER and result in NUMERIC_ORDER:
                result = _wider(result, t)
            else:
                raise TypeCheckError(f"conflicting return types: '{result}' and '{t}'")
        return result

    @staticmethod
    def _literal_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "i64"
        if isinstance(value, float):
            return "f64"
        if isinstance(value, str):
            return "str"
        return "void"


def check(module_ir: Dict[str, Any], frontend_rules: Optional[Dict[str, Any]] = None):
    """Convenience wrapper around :class:`TypeChecker`."""
    return TypeChecker(frontend_rules).check(module_ir)
