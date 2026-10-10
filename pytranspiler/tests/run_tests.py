#!/usr/bin/env python3
"""Validation harness for pytranspiler.

Covers every roadmap phase:

* golden/snapshot comparison of backend output for all cases and targets,
* **native execution** of generated code: the x86_64 assembly is assembled
  and linked against a generated C driver, and the C backend output is
  compiled directly.  Runtime results are compared with the original Python
  functions,
* negative tests for frontend / type-checker / backend errors,
* JSON-Schema validation of every file under ``rules/``.

Run with::

    python3 tests/run_tests.py            # check
    python3 tests/run_tests.py --update   # (re)write the golden files
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # the pytranspiler package directory
CASES_DIR = os.path.join(HERE, "cases")
EXPECTED_DIR = os.path.join(CASES_DIR, "expected")

sys.path.insert(0, ROOT)

import pytranspiler  # noqa: E402
from core import emitter as emitter_mod  # noqa: E402
from core import ir, parser as parser_mod, schema as schema_mod, type_checker  # noqa: E402

# Which targets each case must produce.  04_floats has no x86_64 target
# because the assembly backend is integer-only (documented limitation).
CASE_TARGETS: Dict[str, List[str]] = {
    "01_arithmetic": ["rust", "ruby", "x86_64", "c"],
    "02_variables": ["rust", "ruby", "x86_64", "c"],
    "03_control_flow": ["rust", "ruby", "x86_64", "c"],
    "04_floats": ["rust", "ruby", "c"],
    "05_phi_hoisting": ["rust", "ruby", "x86_64", "c"],
    "06_nested_expr": ["rust", "ruby", "x86_64", "c"],
    "07_functions": ["rust", "ruby", "c"],
    "08_floordiv_mod": ["rust", "ruby", "c"],
    "09_strings": ["rust", "ruby"],
    "10_augassign": ["rust", "ruby", "x86_64", "c"],
    "11_unary_minus": ["rust", "ruby", "x86_64", "c"],
}

# Deterministic sample arguments used when exercising generated functions.
SAMPLES: Dict[int, List[Tuple[int, ...]]] = {
    0: [()],
    1: [(7,), (0,), (-4,)],
    2: [(3, 9), (9, 3), (4, 4)],
    3: [(1, 2, 3), (10, 4, 6)],
    6: [(2, 3, 4, 5, 6, 7), (1, 1, 1, 1, 1, 1)],
}

C_TYPE = {"i64": "long", "f64": "double", "bool": "int", "void": "void", "str": "char *"}


class Results:
    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.passed += 1
            print(f"  PASS  {name}")
        else:
            self.failed += 1
            print(f"  FAIL  {name}")
            if detail:
                for line in detail.splitlines():
                    print(f"        {line}")

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        print(f"  SKIP  {name} ({reason})")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def load_case_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(f"case_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def nasm_to_gas_intel(asm: str) -> str:
    """Translate the NASM subset we emit into GAS Intel syntax for gcc."""
    out = [".intel_syntax noprefix", ".text"]
    for line in asm.splitlines():
        if line.startswith("global "):
            line = ".globl " + line[len("global "):]
        line = re.sub(r"\b(qword|dword|byte)\s+\[", r"\1 ptr [", line)
        out.append(line)
    return "\n".join(out) + "\n"


def collect_calls(transpiler, case_path: str, name: str) -> List[Tuple]:
    """Return (fname, param_types, return_type, args, expected) for a case."""
    source = open(case_path, encoding="utf-8").read()
    module_ir = transpiler.build_ir(source, case_path)
    module = load_case_module(case_path, name)
    calls: List[Tuple] = []
    for fn in module_ir["body"]:
        if fn.get("node") != "FunctionDef":
            continue
        ptypes = [p["type"] for p in fn["params"]]
        ret = fn["return_type"]
        target_fn = getattr(module, fn["name"])
        for sample in SAMPLES.get(len(ptypes), [tuple(range(len(ptypes)))]):
            args = [
                str(a) if t == "str" else (float(a) if t == "f64" else int(a))
                for a, t in zip(sample, ptypes)
            ]
            calls.append((fn["name"], ptypes, ret, args, target_fn(*args)))
    return calls


def _c_literal(value: Any, type_: str) -> str:
    return repr(float(value)) if type_ == "f64" else str(int(value))


def build_c_driver(calls: List[Tuple]) -> str:
    """C driver that calls each generated symbol and prints the result.

    Symbols are aliased to safe C identifiers so Python names that clash
    with C keywords (e.g. ``double``) still link.
    """
    decls, seen = [], set()
    for name, ptypes, ret, _args, _exp in calls:
        if name in seen:
            continue
        seen.add(name)
        params = "void" if not ptypes else ", ".join(C_TYPE.get(t, "long") for t in ptypes)
        decls.append(f'{C_TYPE.get(ret, "long")} tp_{name}({params}) __asm__("{name}");')

    lines = []
    for name, ptypes, ret, args, _exp in calls:
        arglist = ", ".join(_c_literal(a, t) for a, t in zip(args, ptypes))
        if ret == "f64":
            lines.append(f'  printf("%g\\n", (double)tp_{name}({arglist}));')
        else:
            lines.append(f'  printf("%ld\\n", (long)tp_{name}({arglist}));')
    return (
        "#include <stdio.h>\n"
        + "\n".join(decls)
        + "\nint main(void){\n"
        + "\n".join(lines)
        + "\n  return 0;\n}\n"
    )


def run_native(label: str, calls: List[Tuple], generated: str, is_asm: bool, results: Results) -> None:
    cc = shutil.which("tcc") or shutil.which("gcc")
    if cc is None:
        results.skip(label, "no C compiler (tcc/gcc) available")
        return
    with tempfile.TemporaryDirectory() as tmp:
        module_path = os.path.join(tmp, "module.s" if is_asm else "module.c")
        code = nasm_to_gas_intel(generated) if is_asm else generated
        with open(module_path, "w", encoding="utf-8") as handle:
            handle.write(code)
        driver_path = os.path.join(tmp, "driver.c")
        with open(driver_path, "w", encoding="utf-8") as handle:
            handle.write(build_c_driver(calls))
        exe_path = os.path.join(tmp, "prog")
        try:
            subprocess.run(
                [cc, driver_path, module_path, "-o", exe_path],
                check=True, capture_output=True, text=True,
            )
        except (subprocess.CalledProcessError, OSError) as exc:
            results.check(label, False, getattr(exc, "stderr", "") or str(exc))
            return
        out = subprocess.run([exe_path], check=True, capture_output=True, text=True)

    expected = [call[4] for call in calls]
    actual = out.stdout.split()
    ok = len(actual) == len(expected) and all(
        _close(actual[i], expected[i]) for i in range(len(expected))
    )
    results.check(label, ok, f"expected {expected}\nactual   {actual}")


def _close(actual: str, expected: Any) -> bool:
    try:
        value = float(actual)
    except ValueError:
        return False
    return abs(value - float(expected)) < 1e-9


# ---------------------------------------------------------------------------
# test groups
# ---------------------------------------------------------------------------


def test_snapshots(transpiler, results: Results, update: bool) -> None:
    print("\n[snapshots]")
    os.makedirs(EXPECTED_DIR, exist_ok=True)
    for case_name in sorted(CASE_TARGETS):
        case_path = os.path.join(CASES_DIR, case_name + ".py")
        source = open(case_path, encoding="utf-8").read()
        for target in CASE_TARGETS[case_name]:
            output = transpiler.transpile(source, target, case_path)
            golden = os.path.join(EXPECTED_DIR, case_name + transpiler.extension_for(target))
            if update:
                with open(golden, "w", encoding="utf-8") as handle:
                    handle.write(output)
                results.check(f"update {case_name} -> {target}", True)
                continue
            if not os.path.isfile(golden):
                results.check(f"snapshot {case_name} -> {target}", False, "missing golden file (run --update)")
                continue
            expected = open(golden, encoding="utf-8").read()
            results.check(f"snapshot {case_name} -> {target}", output == expected)


def test_runtime(transpiler, results: Results, update: bool) -> None:
    if update:
        return
    print("\n[native runtime]")
    for case_name in sorted(CASE_TARGETS):
        case_path = os.path.join(CASES_DIR, case_name + ".py")
        source = open(case_path, encoding="utf-8").read()
        calls = collect_calls(transpiler, case_path, case_name)
        if "x86_64" in CASE_TARGETS[case_name]:
            asm = transpiler.transpile(source, "x86_64", case_path)
            run_native(f"x86_64 runtime: {case_name}", calls, asm, True, results)
        if "c" in CASE_TARGETS[case_name]:
            c_code = transpiler.transpile(source, "c", case_path)
            run_native(f"c runtime: {case_name}", calls, c_code, False, results)


def test_negative(results: Results) -> None:
    print("\n[negative cases]")
    transpiler = pytranspiler.Transpiler()

    def expect_error(name: str, source: str, exc_types, target: str = "rust", check_line: bool = True) -> None:
        try:
            transpiler.transpile(source, target, "<test>")
        except exc_types as exc:
            msg = str(exc)
            if check_line and "line" not in msg:
                results.check(name, False, f"expected line number in error, got: {msg}")
                return
            results.check(name, True, msg)
            return
        except Exception as exc:  # noqa: BLE001
            results.check(name, False, f"unexpected {type(exc).__name__}: {exc}")
            return
        results.check(name, False, "expected an error but transpilation succeeded")

    expect_error("undefined variable", "def f() -> int:\n    return x\n",
                 type_checker.TypeCheckError)
    expect_error("type mismatch", 'def f() -> int:\n    return 1 + "a"\n',
                 type_checker.TypeCheckError)
    expect_error("unsupported syntax (for)",
                 "def f() -> int:\n    for i in range(3):\n        pass\n    return 0\n",
                 parser_mod.FrontendError)
    expect_error("float on x86_64",
                 "def f(x: float) -> float:\n    return x * 2.0\n",
                 emitter_mod.EmitterError, target="x86_64")
    expect_error("annotated return conflict",
                 "def f() -> int:\n    return 1 + 2.5\n",
                 type_checker.TypeCheckError)
    expect_error("conflicting types for one local",
                 'def f():\n    x = 1\n    x = "a"\n    return x\n',
                 type_checker.TypeCheckError)


def test_schema_validation(results: Results) -> None:
    print("\n[rules schema validation]")
    errors = pytranspiler.check_rules()
    results.check("rules/ files validate", not errors, "\n".join(errors))

    schema = schema_mod.load_schema(os.path.join(ROOT, "schemas", "backend.schema.json"))
    bad = {"target": "x", "templates": {"Var": "{name}"}}  # missing "mode"
    results.check("schema rejects missing 'mode'", bool(schema_mod.validate(bad, schema)))
    good = {"target": "x", "mode": "literal", "templates": {}}
    results.check("schema accepts a valid document", not schema_mod.validate(good, schema))


def test_ir_contract(results: Results) -> None:
    print("\n[IR contract]")
    source = "def add(a: int, b: int) -> int:\n    return a + b\n"
    module = parser_mod.parse(source, pytranspiler.Transpiler().frontend_rules)
    results.check("IR validates", ir.validate(module) is None)

    broken = ir.module([{"node": "BinOp", "op": "ADD"}])
    try:
        ir.validate(broken)
        results.check("IR validation catches bad node", False, "no error raised")
    except ir.IRValidationError:
        results.check("IR validation catches bad node", True)

    body = module["body"]
    results.check("module unit", module["unit"] == "module")
    results.check(
        "function shape",
        body[0]["node"] == "FunctionDef"
        and body[0]["params"][0] == {"name": "a", "type": "i64"},
    )


def test_extensibility(transpiler, results: Results) -> None:
    print("\n[phase 5: extensibility]")
    results.check(
        "C target discovered from rules only",
        "c" in transpiler.available_targets(),
    )


def main(argv: List[str]) -> int:
    update = "--update" in argv
    transpiler = pytranspiler.Transpiler()
    results = Results()
    test_snapshots(transpiler, results, update)
    test_runtime(transpiler, results, update)
    test_negative(results)
    test_schema_validation(results)
    test_ir_contract(results)
    test_extensibility(transpiler, results)

    print(f"\n{results.passed} passed, {results.failed} failed, {results.skipped} skipped")
    return 1 if results.failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
