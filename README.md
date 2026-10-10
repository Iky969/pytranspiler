# pytranspiler

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

## Usage

```bash
cd pytranspiler

# list targets / validate the rule files
python3 pytranspiler.py --list-targets
python3 pytranspiler.py --check-rules

# transpile (writes <input>.rs next to the current directory)
python3 pytranspiler.py tests/cases/01_arithmetic.py -t rust
python3 pytranspiler.py tests/cases/03_control_flow.py -t x86_64 -o control.asm
python3 pytranspiler.py tests/cases/02_variables.py -t c -o -

# inspect the Canonical IR
python3 pytranspiler.py tests/cases/01_arithmetic.py --dump-ir
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
missing `type` attributes (so `x = 10` is inferred as `i64`) and rejects
ill-typed programs.

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
| 3 | Type inference & variables (`Assign`, `Var`, no manual annotations) | ✅ |
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

## Limitations

* Supported source subset: module-level functions, `int`/`float`/`bool`
  expressions, `+ - * / // %`, comparisons, `and`/`or`, `not`, unary `-`,
  assignments, `if/elif/else`, `while`, `return` and `print(...)`.
* The x86_64 backend is integer-only (no floats, strings or calls) and follows
  the System V ABI with at most six register arguments.
* Variables are treated as function-scoped (like Python); a variable that is
  *first* assigned inside a conditional branch may need an explicit initial
  value before the branch to map cleanly onto Rust/C scoping.
* `print(...)` uses a generic format (`{:?}` in Rust, `%ld` in C) rather than
  inspecting argument types.
