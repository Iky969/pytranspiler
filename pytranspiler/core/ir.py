"""Canonical Intermediate Representation (IR) for pytranspiler.

Every supported source language is lowered into this neutral, JSON
serialisable structure *before* any backend touches it.  The shape is
intentionally language neutral: it contains no Python AST objects and no
target-language syntax, only the semantics that every backend understands.

The IR is a plain ``dict`` (so it can be dumped to / loaded from JSON)
shaped like::

    {
      "unit": "module",
      "body": [ <node>, ... ]
    }

Every node carries a ``"node"`` key naming its kind.  Literal values use
``type`` strings from the shared type vocabulary (:data:`KNOWN_TYPES`)
which backends map onto their own type names.

The example from the project specification maps onto::

    function_def(
        name="add",
        params=[param("a", "i64"), param("b", "i64")],
        return_type="i64",
        body=[ret(bin_op("ADD", var("a"), var("b")))],
    )
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

# ---------------------------------------------------------------------------
# Node kind constants
# ---------------------------------------------------------------------------

UNIT_MODULE = "module"

FUNCTION_DEF = "FunctionDef"
RETURN = "Return"
ASSIGN = "Assign"
IF = "If"
WHILE = "While"
BIN_OP = "BinOp"
UNARY_OP = "UnaryOp"
COMPARE = "Compare"
CALL = "Call"
VAR = "Var"
LITERAL = "Literal"

#: All statement node kinds (nodes that may appear inside a ``body`` list).
STATEMENT_KINDS = frozenset({FUNCTION_DEF, RETURN, ASSIGN, IF, WHILE, CALL})

#: All expression node kinds.
EXPRESSION_KINDS = frozenset({BIN_OP, UNARY_OP, COMPARE, CALL, VAR, LITERAL})

ALL_KINDS = STATEMENT_KINDS | EXPRESSION_KINDS

#: The neutral type vocabulary understood by the type checker.  Backends map
#: these onto concrete target types through ``rules/backends/*.json``.
KNOWN_TYPES = frozenset({"i64", "f64", "bool", "str", "void"})

#: Numeric promotion order used during type unification.
NUMERIC_ORDER = {"bool": 0, "i64": 1, "f64": 2}


class IRValidationError(ValueError):
    """Raised when an IR tree does not match the canonical contract."""


# ---------------------------------------------------------------------------
# Node constructors
# ---------------------------------------------------------------------------


def module(body: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a canonical IR module."""
    return {"unit": UNIT_MODULE, "body": list(body)}


def function_def(
    name: str,
    params: List[Dict[str, Any]],
    return_type: Optional[str],
    body: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "node": FUNCTION_DEF,
        "name": name,
        "params": list(params),
        "return_type": return_type,
        "body": list(body),
    }


def param(name: str, type_: Optional[str] = None) -> Dict[str, Any]:
    return {"name": name, "type": type_}


def ret(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {"node": RETURN, "value": value}


def assign(target: str, value: Dict[str, Any]) -> Dict[str, Any]:
    return {"node": ASSIGN, "target": target, "value": value, "type": None}


def if_(test: Dict[str, Any], body: Iterable[Dict[str, Any]],
        orelse: Optional[Iterable[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return {
        "node": IF,
        "test": test,
        "body": list(body),
        "orelse": list(orelse or []),
    }


def while_(test: Dict[str, Any], body: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {"node": WHILE, "test": test, "body": list(body)}


def bin_op(op: str, left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {"node": BIN_OP, "op": op, "left": left, "right": right, "type": None}


def unary_op(op: str, operand: Dict[str, Any]) -> Dict[str, Any]:
    return {"node": UNARY_OP, "op": op, "operand": operand, "type": None}


def compare(op: str, left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    return {"node": COMPARE, "op": op, "left": left, "right": right, "type": None}


def call(func: str, args: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {"node": CALL, "func": func, "args": list(args), "type": None}


def var(name: str, type_: Optional[str] = None) -> Dict[str, Any]:
    return {"node": VAR, "name": name, "type": type_}


def literal(value: Any, type_: Optional[str] = None) -> Dict[str, Any]:
    return {"node": LITERAL, "value": value, "type": type_}


# ---------------------------------------------------------------------------
# Traversal helpers
# ---------------------------------------------------------------------------


def iter_child_expressions(node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the direct expression children of *node* (if any)."""
    kind = node.get("node")
    if kind == RETURN:
        return [node["value"]] if node.get("value") else []
    if kind == ASSIGN:
        return [node["value"]]
    if kind == IF:
        return [node["test"]]
    if kind == WHILE:
        return [node["test"]]
    if kind in (BIN_OP, COMPARE):
        return [node["left"], node["right"]]
    if kind == UNARY_OP:
        return [node["operand"]]
    if kind == CALL:
        return list(node.get("args", []))
    return []


def walk(node: Dict[str, Any]):
    """Yield *node* and every nested node depth-first."""
    yield node
    for child in iter_child_expressions(node):
        yield from walk(child)
    if node.get("node") == FUNCTION_DEF:
        for stmt in node.get("body", []):
            yield from walk(stmt)
    elif node.get("node") == IF:
        for stmt in node.get("body", []):
            yield from walk(stmt)
        for stmt in node.get("orelse", []):
            yield from walk(stmt)
    elif node.get("node") == WHILE:
        for stmt in node.get("body", []):
            yield from walk(stmt)


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------

_REQUIRED_KEYS: Dict[str, tuple] = {
    FUNCTION_DEF: ("name", "params", "body"),
    RETURN: ("value",),
    ASSIGN: ("target", "value"),
    IF: ("test", "body", "orelse"),
    WHILE: ("test", "body"),
    BIN_OP: ("op", "left", "right"),
    UNARY_OP: ("op", "operand"),
    COMPARE: ("op", "left", "right"),
    CALL: ("func", "args"),
    VAR: ("name",),
    LITERAL: ("value",),
}


def validate(module_ir: Dict[str, Any]) -> None:
    """Validate an IR tree against the canonical contract.

    Raises :class:`IRValidationError` on the first violation found.
    """
    if not isinstance(module_ir, dict) or module_ir.get("unit") != UNIT_MODULE:
        raise IRValidationError("root must be a module with unit == 'module'")
    if not isinstance(module_ir.get("body"), list):
        raise IRValidationError("module.body must be a list")

    for stmt in module_ir["body"]:
        _validate_node(stmt, path="module.body")


def _validate_node(node: Any, path: str) -> None:
    if not isinstance(node, dict):
        raise IRValidationError(f"{path}: expected a node object, got {type(node).__name__}")
    kind = node.get("node")
    if kind not in ALL_KINDS:
        raise IRValidationError(f"{path}: unknown node kind {kind!r}")
    for key in _REQUIRED_KEYS[kind]:
        if key not in node:
            raise IRValidationError(f"{path}.{kind}: missing required key {key!r}")

    # Validate declared types.
    for type_val, where in _declared_types(node):
        if type_val is not None and type_val not in KNOWN_TYPES:
            raise IRValidationError(f"{path}: unknown type {type_val!r} at {where}")

    # Recurse into children.
    if kind == FUNCTION_DEF:
        if not isinstance(node["params"], list):
            raise IRValidationError(f"{path}.{FUNCTION_DEF}: params must be a list")
        for i, p in enumerate(node["params"]):
            if not isinstance(p, dict) or "name" not in p:
                raise IRValidationError(f"{path}.params[{i}]: must be a {{name, type}} object")
        for i, stmt in enumerate(node["body"]):
            _validate_node(stmt, f"{path}.body[{i}]")
    elif kind == IF:
        _validate_node(node["test"], f"{path}.test")
        for i, stmt in enumerate(node["body"]):
            _validate_node(stmt, f"{path}.body[{i}]")
        for i, stmt in enumerate(node["orelse"]):
            _validate_node(stmt, f"{path}.orelse[{i}]")
    elif kind == WHILE:
        _validate_node(node["test"], f"{path}.test")
        for i, stmt in enumerate(node["body"]):
            _validate_node(stmt, f"{path}.body[{i}]")
    else:
        for i, child in enumerate(iter_child_expressions(node)):
            _validate_node(child, f"{path}.child[{i}]")


def _declared_types(node: Dict[str, Any]):
    kind = node.get("node")
    if kind in (VAR, LITERAL, ASSIGN, BIN_OP, UNARY_OP, COMPARE, CALL):
        yield node.get("type"), "type"
    if kind == FUNCTION_DEF:
        yield node.get("return_type"), "return_type"
        for i, p in enumerate(node.get("params", [])):
            yield p.get("type"), f"params[{i}].type"
