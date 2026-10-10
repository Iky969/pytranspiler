"""A tiny, dependency-free JSON-Schema validator.

Phase 5 of the roadmap requires validating every file under ``rules/``
against a JSON Schema so that new targets can be added safely.  Rather than
pulling in a third-party dependency, this module implements the subset of
the JSON-Schema vocabulary that the project's schemas actually use:
``type``, ``required``, ``properties``, ``additionalProperties``,
``patternProperties``, ``items``, ``enum``, ``const``, ``minimum``,
``minItems``, ``minLength``, ``anyOf`` and local ``$ref`` resolution.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


class SchemaError(ValueError):
    """Raised by :func:`validate_or_raise` when a document is invalid."""


def _type_matches(value: Any, type_name: str) -> bool:
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    expected = _JSON_TYPES.get(type_name)
    if expected is None:
        return True  # unknown type keyword: don't fail the document
    return isinstance(value, expected)


def _resolve_ref(ref: str, root: Dict[str, Any]) -> Dict[str, Any]:
    if not ref.startswith("#/"):
        raise SchemaError(f"unsupported $ref target: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def validate(instance: Any, schema: Dict[str, Any], root: Dict[str, Any] = None,
             path: str = "$") -> List[str]:
    """Return a list of human-readable error strings (empty means valid)."""
    if root is None:
        root = schema
    errors: List[str] = []

    if "$ref" in schema:
        return validate(instance, _resolve_ref(schema["$ref"], root), root, path)

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected {schema['const']!r}, got {instance!r}")

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']!r}")

    if "type" in schema:
        types = schema["type"]
        types = types if isinstance(types, list) else [types]
        if not any(_type_matches(instance, t) for t in types):
            errors.append(f"{path}: expected type {schema['type']!r}, got {type(instance).__name__}")
            return errors

    if "anyOf" in schema and not any(
        not validate(instance, sub, root, path) for sub in schema["anyOf"]
    ):
        errors.append(f"{path}: value does not match any allowed schema")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property '{key}'")
        properties = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            child_path = f"{path}.{key}"
            matched = False
            if key in properties:
                matched = True
                errors.extend(validate(value, properties[key], root, child_path))
            for pattern, sub in patterns.items():
                if re.search(pattern, key):
                    matched = True
                    errors.extend(validate(value, sub, root, child_path))
            if not matched:
                if additional is False:
                    errors.append(f"{child_path}: additional property not allowed")
                elif isinstance(additional, dict):
                    errors.extend(validate(value, additional, root, child_path))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, value in enumerate(instance):
                errors.extend(validate(value, items, root, f"{path}[{i}]"))

    if isinstance(instance, str) and "minLength" in schema:
        if len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than {schema['minLength']}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} is below minimum {schema['minimum']}")

    return errors


def validate_or_raise(instance: Any, schema: Dict[str, Any], label: str = "document") -> None:
    errors = validate(instance, schema)
    if errors:
        joined = "\n  - ".join(errors)
        raise SchemaError(f"{label} failed schema validation:\n  - {joined}")


def load_schema(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
