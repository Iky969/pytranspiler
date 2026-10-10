"""Frontend: lower Python source into the Canonical IR.

This is a thin, data-driven wrapper around the standard library
:mod:`ast` module.  The only thing that is *not* hard-coded here are the
operator / type mappings, which are read from
``rules/frontends/python.json`` so that the frontend can be extended
without editing this file.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional

from . import ir


class FrontendError(SyntaxError):
    """Raised when the Python source cannot be lowered into the IR."""


class PythonFrontend:
    """Lower a Python module into the Canonical IR."""

    def __init__(self, rules: Dict[str, Any]):
        self.rules = rules
        self.binop_ops: Dict[str, str] = rules.get("binop_ops", {})
        self.unary_ops: Dict[str, str] = rules.get("unary_ops", {})
        self.compare_ops: Dict[str, str] = rules.get("compare_ops", {})
        self.type_hints: Dict[str, str] = rules.get("type_hints", {})
        self.literal_types: Dict[str, str] = rules.get("literal_types", {})

    # -- entry point --------------------------------------------------------

    def parse(self, source: str, filename: str = "<unknown>") -> Dict[str, Any]:
        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as exc:  # pragma: no cover - passthrough
            raise FrontendError(str(exc)) from exc
        body = [self.lower_stmt(stmt) for stmt in tree.body if not self._is_docstring(stmt)]
        body = [node for node in body if node is not None]
        return ir.module(body)

    # -- statements ---------------------------------------------------------

    def lower_stmt(self, node: ast.stmt) -> Optional[Dict[str, Any]]:
        if isinstance(node, ast.FunctionDef):
            return self._lower_function(node)
        if isinstance(node, ast.Return):
            value = self.lower_expr(node.value) if node.value is not None else None
            return ir.ret(value)
        if isinstance(node, ast.Assign):
            return self._lower_assign(node)
        if isinstance(node, ast.AugAssign):
            return self._lower_augassign(node)
        if isinstance(node, ast.AnnAssign):
            return self._lower_annassign(node)
        if isinstance(node, ast.If):
            return ir.if_(
                self.lower_expr(node.test),
                [self.lower_stmt(s) for s in node.body if not self._is_docstring(s)],
                [self.lower_stmt(s) for s in node.orelse if not self._is_docstring(s)],
            )
        if isinstance(node, ast.While):
            return ir.while_(
                self.lower_expr(node.test),
                [self.lower_stmt(s) for s in node.body if not self._is_docstring(s)],
            )
        if isinstance(node, ast.Expr):
            return self.lower_expr(node.value)
        if isinstance(node, ast.Pass):
            return None
        raise FrontendError(f"unsupported statement: {type(node).__name__} (line {node.lineno})")

    def _lower_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        params = [self._lower_arg(a) for a in node.args.args]
        if node.args.vararg or node.args.kwarg or node.args.kwonlyargs or node.args.posonlyargs:
            raise FrontendError(
                f"function '{node.name}': only positional parameters are supported"
            )
        return_type = self._resolve_annotation(node.returns)
        body = [self.lower_stmt(s) for s in node.body if not self._is_docstring(s)]
        body = [s for s in body if s is not None]
        return ir.function_def(node.name, params, return_type, body)

    def _lower_arg(self, arg: ast.arg) -> Dict[str, Any]:
        return ir.param(arg.arg, self._resolve_annotation(arg.annotation))

    def _lower_assign(self, node: ast.Assign) -> Dict[str, Any]:
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise FrontendError(
                f"unsupported assignment target (line {node.lineno}); "
                "only simple 'name = expr' is supported"
            )
        return ir.assign(node.targets[0].id, self.lower_expr(node.value))

    def _lower_annassign(self, node: ast.AnnAssign) -> Dict[str, Any]:
        if not isinstance(node.target, ast.Name):
            raise FrontendError(f"unsupported annotated target (line {node.lineno})")
        if node.value is None:
            raise FrontendError(f"annotated assignment needs a value (line {node.lineno})")
        node_ir = ir.assign(node.target.id, self.lower_expr(node.value))
        node_ir["type"] = self._resolve_annotation(node.annotation)
        return node_ir

    def _lower_augassign(self, node: ast.AugAssign) -> Dict[str, Any]:
        if not isinstance(node.target, ast.Name):
            raise FrontendError(f"unsupported augmented target (line {node.lineno})")
        name = node.target.id
        op = self.binop_ops.get(type(node.op).__name__)
        if op is None:
            raise FrontendError(f"unsupported augmented operator (line {node.lineno})")
        combined = ir.bin_op(op, ir.var(name), self.lower_expr(node.value))
        return ir.assign(name, combined)

    # -- expressions --------------------------------------------------------

    def lower_expr(self, node: ast.expr) -> Dict[str, Any]:
        if isinstance(node, ast.BinOp):
            op = self.binop_ops.get(type(node.op).__name__)
            if op is None:
                raise FrontendError(
                    f"unsupported binary operator {type(node.op).__name__} (line {node.lineno})"
                )
            return ir.bin_op(op, self.lower_expr(node.left), self.lower_expr(node.right))
        if isinstance(node, ast.UnaryOp):
            op = self.unary_ops.get(type(node.op).__name__)
            if op is None:
                raise FrontendError(
                    f"unsupported unary operator {type(node.op).__name__} (line {node.lineno})"
                )
            return ir.unary_op(op, self.lower_expr(node.operand))
        if isinstance(node, ast.Compare):
            return self._lower_compare(node)
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise FrontendError(f"unsupported call target (line {node.lineno})")
            return ir.call(node.func.id, [self.lower_expr(a) for a in node.args])
        if isinstance(node, ast.Name):
            return ir.var(node.id)
        if isinstance(node, ast.Constant):
            return self._lower_constant(node)
        raise FrontendError(f"unsupported expression: {type(node).__name__} (line {node.lineno})")

    def _lower_compare(self, node: ast.Compare) -> Dict[str, Any]:
        if len(node.ops) != 1:
            # Lower chained comparisons as nested AND-style compares.
            result = None
            left = node.left
            for op, right in zip(node.ops, node.comparators):
                mapped = self.compare_ops.get(type(op).__name__)
                if mapped is None:
                    raise FrontendError(f"unsupported comparison (line {node.lineno})")
                cmp = ir.compare(mapped, self.lower_expr(left), self.lower_expr(right))
                result = cmp if result is None else ir.bin_op("AND", result, cmp)
                left = right
            return result  # type: ignore[return-value]
        mapped = self.compare_ops.get(type(node.ops[0]).__name__)
        if mapped is None:
            raise FrontendError(f"unsupported comparison (line {node.lineno})")
        return ir.compare(mapped, self.lower_expr(node.left), self.lower_expr(node.comparators[0]))

    def _lower_constant(self, node: ast.Constant) -> Dict[str, Any]:
        value = node.value
        if isinstance(value, bool):
            return ir.literal(value, self.literal_types.get("bool", "bool"))
        if isinstance(value, int):
            return ir.literal(value, self.literal_types.get("int", "i64"))
        if isinstance(value, float):
            return ir.literal(value, self.literal_types.get("float", "f64"))
        if isinstance(value, str):
            return ir.literal(value, self.literal_types.get("str", "str"))
        if value is None:
            return ir.literal(None, self.literal_types.get("none", "void"))
        raise FrontendError(f"unsupported literal: {value!r}")

    # -- helpers ------------------------------------------------------------

    def _resolve_annotation(self, annotation: Optional[ast.expr]) -> Optional[str]:
        if annotation is None:
            return None
        if isinstance(annotation, ast.Name):
            name = annotation.id
        elif isinstance(annotation, ast.Constant) and annotation.value is None:
            name = "None"
        else:
            raise FrontendError(f"unsupported type annotation: {ast.dump(annotation)}")
        if name not in self.type_hints:
            raise FrontendError(f"unknown type annotation: {name!r}")
        return self.type_hints[name]

    @staticmethod
    def _is_docstring(node: ast.stmt) -> bool:
        return (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )


def parse(source: str, rules: Dict[str, Any], filename: str = "<unknown>") -> Dict[str, Any]:
    """Convenience wrapper: lower *source* using *rules*."""
    return PythonFrontend(rules).parse(source, filename)
