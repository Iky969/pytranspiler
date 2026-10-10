# pytranspiler

[![CI](https://github.com/Rzy/pytranspiler/actions/workflows/ci.yml/badge.svg)](https://github.com/Rzy/pytranspiler/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

A modular, **rule-driven** transpiler that lowers a subset of Python into
Rust, Ruby, C and x86_64 assembly.

The design follows the specification in [`Jobs.md`](./Jobs.md):

```
[ Python source ]
        │
        ▼
   ┌──────────┐  ◄── rules/frontends/python.json
   │ Frontend │        (Python AST → Canonical IR)
   └────┬─────┘
        ▼
   ┌───────────┐
   │ Canonical │  ◄── core/type_checker.py
   │    IR     │        (type & scope resolution)
   └────┬──────┘
        ▼
   ┌──────────┐  ◄── rules/backends/<target>.json
   │ Backend  │        (IR → target code)
   └────┬─────┘
        ▼
[ Rust | Ruby | C | x86_64 assembly ]
```

Every language/target is described by a **JSON rule file**, so adding a new
target means adding a file under `rules/backends/` — no Python changes.

## Documentation

* [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — repository layout, pipeline
  stages, the Canonical IR and its passes, rule-file formats, and how the two
  emitter strategies work.
* [`docs/DEVELOPMENT.md`](./docs/DEVELOPMENT.md) — ground rules, how to run and
  verify, step-by-step recipes for adding a target / IR node / test case, and a
  prioritised roadmap (semantics gaps, x86_64 depth, language coverage,
  extensibility, packaging & CI, performance).

## Directory structure

```
pytranspiler/
├── pytranspiler.py            # CLI entrypoint (argument parsing, orchestration)
├── core/
│   ├── parser.py              # wrapper around the built-in Python `ast` module
│   ├── ir.py                  # Canonical IR node definitions + validation
│   ├── type_checker.py        # type inference & validation
│   ├── emitter.py             # template engine (IR → target) + x86_64 codegen
│   └── schema.py              # dependency-free JSON-Schema validator (Phase 5)
├── rules/
│   ├── frontends/
│   │   └── python.json        # Python AST → IR mapping rules
│   └── backends/
│       ├── rust.json          # Rust templates
│       ├── ruby.json          # Ruby templates
│       ├── c.json             # C templates
│       └── x86_64.json        # x86_64 (System V, NASM) rules + register model
├── schemas/                   # JSON-Schema for the rule files and the IR
│   ├── frontend.schema.json
│   ├── backend.schema.json
│   └── ir.schema.json
└── tests/
    ├── run_tests.py           # validation harness
    └── cases/                 # compilation test programs (+ expected/ snapshots)
```

## Installation & Usage

```bash
# install locally in editable mode
pip install -e .

# list targets / validate the rule files
pytranspiler --list-targets
pytranspiler --check-rules

# transpile (writes <input>.<ext> by default or use -o)
pytranspiler examples/fibonacci.py -t rust
pytranspiler examples/collatz.py -t x86_64 -o collatz.asm
pytranspiler examples/gcd.py -t c -o -

# inspect the Canonical IR
pytranspiler examples/power.py --dump-ir
```

Rust/Ruby/C support: arithmetic, variables, `if/elif/else`, `while`, comparisons,
`print(...)`, and `int`/`float`/`bool` inference. The x86_64 backend supports the
same control flow and integer arithmetic (no floating point or calls).

## The Canonical IR

`core/parser.py` lowers the Python AST into a neutral, JSON-serialisable tree.
For example:

```python
def add(a: int, b: int) -> int:
    return a + b
```

becomes

```json
{
  "unit": "module",
  "body": [{
    "node": "FunctionDef",
    "name": "add",
    "params": [{"name": "a", "type": "i64"}, {"name": "b", "type": "i64"}],
    "return_type": "i64",
    "body": [{
      "node": "Return",
      "value": {
        "node": "BinOp", "op": "ADD",
        "left": {"node": "Var", "name": "a", "type": "i64"},
        "right": {"node": "Var", "name": "b", "type": "i64"}
      }
    }]
  }]
}
```

`core/ir.py` validates this structure; `core/type_checker.py` fills in any
missing `type` attributes (so `x = 10` is inferred as `i64`), rejects
ill-typed programs, and hoists every local binding onto the enclosing function
(see [Design hardening §1](#1-variable-scoping-and-the-phi-node-case)).

## Adding a new target

1. Create `rules/backends/<name>.json` with `target`, `mode`, `templates`,
   `operators`, types, etc. (see `c.json` for a complete literal example).
2. That's it — the CLI discovers it, `--check-rules` validates it against
   `schemas/backend.schema.json`, and `-t <name>` works immediately.

## Roadmap status

| Phase | Milestone | Status |
|---|---|---|
| 1 | Scalar pipeline — `pytranspiler.py`, `ir.py`, `emitter.py`, `rust.json`, `ruby.json` | ✅ |
| 2 | x86_64 assembly backend + simple register/frame allocation | ✅ |
| 3 | Type inference & variables (`Assign`, `Var`, no manual annotations) | ✅ (plus a variable-hoisting pass) |
| 4 | Control flow (`If`, `While`, `Compare`, unique labels) | ✅ |
| 5 | Modular extensibility + JSON-Schema validation of `rules/` | ✅ (adds a C target with no Python changes) |

## Testing

```bash
python3 tests/run_tests.py            # run all checks
python3 tests/run_tests.py --update   # refresh the golden snapshots
```

The harness verifies:

* golden/snapshot output for every case × target,
* **native execution**: generated x86_64 assembly is assembled and linked with
  `gcc`, generated C is compiled directly, and the runtime results are compared
  against the original Python functions,
* negative cases (undefined variables, type errors, unsupported syntax),
* JSON-Schema validation of the rule files, and the IR contract.

## Design hardening

Four failure modes were analysed and are handled as follows.

### 1. Variable scoping and the "phi-node" case

Python scopes a variable to the whole function, so

```python
if flag > 0:
    x = 10
else:
    x = 20
return x
```

must survive lowering to targets with **block scope**.  Emitting `let x = 10;`
inside the branch would kill `x` at the closing brace (Rust) or hide it from the
enclosing block (C), so the naive output does not compile.

`core/type_checker.py` therefore runs a **variable-hoisting pass**: before
emission it collects every non-parameter local in first-appearance order,
unifies the types of all of its assignments (widening numerics, rejecting
genuine conflicts) and records them on the function as `locals`.  Backends that
set `"hoist_locals": true` (Rust, C) declare every local once in the prologue
via the `Local` template and treat *all* assignments as plain reassignments:

```rust
pub fn choose(flag: i64) -> i64 {
    let mut x: i64;
    if (flag > 0) { x = 10; } else { x = 20; }
    return x;
}
```

The x86_64 backend already reserved one fixed `[rbp-N]` slot per local, so a
variable assigned in either branch lands in the same slot; Ruby variables are
function-scoped to begin with, so neither needs the prologue.

### 2. Compound expressions and register pressure

The x86_64 backend does **not** attempt graph-colouring allocation.  It uses
**stack-based evaluation**: the left operand is `push`ed to the machine stack,
the right operand is evaluated into the accumulator, and the operation pops the
left operand back.  Register pressure is constant (one accumulator plus one
scratch register) regardless of nesting depth, so
`(a + b) * (c - d) + (e * f)` lowers correctly with only one spill slot live at
a time.

### 3. System V 16-byte stack alignment

At function entry `call` has pushed an 8-byte return address (`rsp % 16 == 8`);
after `push rbp` the stack is 16-byte aligned.  Frame allocation rounds the
reserved size up to the next multiple of `stack_alignment`
(`core/emitter.py: AsmEmitter._align_frame`), so `sub rsp, N` always keeps `rsp`
16-byte aligned — the prerequisite for calling into libc/SSE code later.  The
harness asserts every emitted frame is a multiple of 16.

### 4. Integer overflow semantics

Python integers are arbitrary precision; the backends emit **64-bit two's
complement** (`i64` in Rust, `long` in C, `rax`/`[rbp-N]` in assembly).  Input
programs are therefore assumed to stay within `INT64_MIN..INT64_MAX`:

* in-range arithmetic is bit-identical to Python;
* out-of-range arithmetic **wraps** in C and in Rust release builds, while Rust
  **debug** builds panic on overflow;
* Python's big-integer results are not representable and are not emulated.

## Examples

The `examples/` directory contains realistic programs that demonstrate the
transpiler's capabilities:

```bash
# Fibonacci sequence (iterative)
pytranspiler examples/fibonacci.py -t rust
pytranspiler examples/fibonacci.py -t c -o fibonacci.c

# Greatest common divisor
pytranspiler examples/gcd.py -t ruby

# Collatz conjecture steps
pytranspiler examples/collatz.py -t x86_64 -o collatz.asm

# Integer exponentiation
pytranspiler examples/power.py -t c -o -
```

## Limitations

* Supported source subset: module-level functions, user-defined function calls
  (including recursion), `int`/`float`/`bool`/`str` expressions (with string concatenation
  and f-strings), `+ - * / // %` (Python-compliant floor division and modulo semantics
  on Rust/Ruby/C), comparisons, `and`/`or`, `not`, unary `-`, assignments,
  `if/elif/else`, `while`, `return` and `print(...)`.
* The x86_64 backend is integer-only (no floats, strings or calls) and follows
  the System V ABI with at most six register arguments.
* Values are 64-bit two's complement (see §4 above), not Python big integers.
* A hoisted local must be assigned on every path before it is used, mirroring
  Rust/C definite-initialization rules; a variable assigned in only one branch
  of an `if` and read afterwards is rejected by the target compiler.
* `print(...)` uses a generic format (`{:?}` in Rust, `%ld` in C) rather than
  inspecting argument types.
