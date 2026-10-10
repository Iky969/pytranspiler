#!/usr/bin/env python3
"""pytranspiler -- a modular, rule-driven Python transpiler.

Pipeline:  [Python source] -> Frontend -> Canonical IR -> Type Resolution
           -> Backend -> [Rust | Ruby | x86_64 assembly]

Examples
--------
    python3 pytranspiler.py examples/add.py -t rust
    python3 pytranspiler.py examples/add.py -t x86_64 -o add.asm
    python3 pytranspiler.py examples/add.py --dump-ir
    python3 pytranspiler.py --check-rules
    python3 pytranspiler.py --list-targets
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import emitter as emitter_mod  # noqa: E402
from core import ir, parser as parser_mod, type_checker  # noqa: E402
from core import schema as schema_mod  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RULES_DIR = os.path.join(HERE, "rules")
SCHEMAS_DIR = os.path.join(HERE, "schemas")


class TranspilerError(RuntimeError):
    """Raised for configuration / rule loading problems."""


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


class Transpiler:
    """High level orchestration of the transpile pipeline."""

    def __init__(self, rules_dir: str = DEFAULT_RULES_DIR, validate_rules: bool = True):
        self.rules_dir = rules_dir
        self.frontend_path = os.path.join(rules_dir, "frontends", "python.json")
        if not os.path.isfile(self.frontend_path):
            raise TranspilerError(f"frontend rule file not found: {self.frontend_path}")
        self.frontend_rules = _load_json(self.frontend_path)
        if validate_rules:
            _validate_document(self.frontend_rules, "frontend.schema.json", self.frontend_path)
        self._backend_cache: Dict[str, Dict[str, Any]] = {}

    # -- rule loading -------------------------------------------------------

    def backend_dir(self) -> str:
        return os.path.join(self.rules_dir, "backends")

    def available_targets(self) -> List[str]:
        directory = self.backend_dir()
        if not os.path.isdir(directory):
            return []
        targets = []
        for name in sorted(os.listdir(directory)):
            if name.endswith(".json"):
                targets.append(os.path.splitext(name)[0])
        return targets

    def load_backend(self, target: str) -> Dict[str, Any]:
        if target in self._backend_cache:
            return self._backend_cache[target]
        path = os.path.join(self.backend_dir(), f"{target}.json")
        if not os.path.isfile(path):
            available = ", ".join(self.available_targets()) or "(none)"
            raise TranspilerError(f"unknown target '{target}'. Available: {available}")
        backend = _load_json(path)
        _validate_document(backend, "backend.schema.json", path)
        self._backend_cache[target] = backend
        return backend

    # -- pipeline -----------------------------------------------------------

    def build_ir(self, source: str, filename: str = "<stdin>") -> Dict[str, Any]:
        module_ir = parser_mod.parse(source, self.frontend_rules, filename)
        ir.validate(module_ir)
        type_checker.check(module_ir, self.frontend_rules)
        return module_ir

    def transpile(self, source: str, target: str, filename: str = "<stdin>") -> str:
        backend = self.load_backend(target)
        module_ir = self.build_ir(source, filename)
        emit = emitter_mod.create_emitter(backend, self.frontend_rules)
        return emit.emit_module(module_ir)

    def extension_for(self, target: str) -> str:
        return self.load_backend(target).get("extension", f".{target}")


# ---------------------------------------------------------------------------
# Rule validation helpers (Phase 5)
# ---------------------------------------------------------------------------


def _validate_document(document: Dict[str, Any], schema_name: str, label: str) -> None:
    schema_path = os.path.join(SCHEMAS_DIR, schema_name)
    if not os.path.isfile(schema_path):
        return  # schemas are optional at runtime
    schema = schema_mod.load_schema(schema_path)
    try:
        schema_mod.validate_or_raise(document, schema, label=label)
    except schema_mod.SchemaError as exc:
        raise TranspilerError(str(exc)) from exc


def check_rules(rules_dir: str = DEFAULT_RULES_DIR) -> List[str]:
    """Validate every rule file. Returns a list of error messages."""
    errors: List[str] = []
    frontends = os.path.join(rules_dir, "frontends")
    backends = os.path.join(rules_dir, "backends")
    jobs = [
        (os.path.join(frontends, "python.json"), "frontend.schema.json"),
    ]
    if os.path.isdir(backends):
        for name in sorted(os.listdir(backends)):
            if name.endswith(".json"):
                jobs.append((os.path.join(backends, name), "backend.schema.json"))
    for path, schema_name in jobs:
        if not os.path.isfile(path):
            errors.append(f"missing rule file: {path}")
            continue
        try:
            document = _load_json(path)
            _validate_document(document, schema_name, path)
        except (TranspilerError, json.JSONDecodeError) as exc:
            errors.append(str(exc))
    return errors


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pytranspiler",
        description="Transpile a subset of Python into Rust, Ruby or x86_64 assembly.",
    )
    parser.add_argument("input", nargs="?", help="input Python source file ('-' for stdin)")
    parser.add_argument("-t", "--target", default="rust", help="backend target (default: rust)")
    parser.add_argument("-o", "--output", help="output file ('-' for stdout)")
    parser.add_argument("--rules-dir", default=DEFAULT_RULES_DIR, help="directory with rule files")
    parser.add_argument("--dump-ir", action="store_true", help="print the Canonical IR and exit")
    parser.add_argument("--list-targets", action="store_true", help="list available targets")
    parser.add_argument("--check-rules", action="store_true", help="validate rules/ and exit")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.check_rules:
        errors = check_rules(args.rules_dir)
        if errors:
            print("rule validation FAILED:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        print("all rule files are valid")
        return 0

    try:
        transpiler = Transpiler(rules_dir=args.rules_dir)
    except TranspilerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.list_targets:
        for target in transpiler.available_targets():
            print(target)
        return 0

    if not args.input:
        build_arg_parser().error("an input file is required (or use --check-rules / --list-targets)")

    if args.input == "-":
        source = sys.stdin.read()
        filename = "<stdin>"
    else:
        if not os.path.isfile(args.input):
            print(f"error: input file not found: {args.input}", file=sys.stderr)
            return 2
        with open(args.input, "r", encoding="utf-8") as handle:
            source = handle.read()
        filename = args.input

    try:
        if args.dump_ir:
            module_ir = transpiler.build_ir(source, filename)
            print(json.dumps(module_ir, indent=2))
            return 0

        output = transpiler.transpile(source, args.target, filename)
    except (parser_mod.FrontendError, type_checker.TypeCheckError, ir.IRValidationError,
            emitter_mod.EmitterError, TranspilerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    destination = args.output
    if destination in (None, "-"):
        if destination == "-":
            sys.stdout.write(output)
            return 0
        stem = os.path.splitext(os.path.basename(args.input))[0] if args.input != "-" else "out"
        destination = stem + transpiler.extension_for(args.target)

    with open(destination, "w", encoding="utf-8") as handle:
        handle.write(output)
    print(f"wrote {destination} ({args.target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
