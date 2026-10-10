# Architecture

`pytranspiler` is a modular, **rule-driven** compiler front-to-back. It lowers a
subset of Python into a neutral Canonical IR and then emits Rust, Ruby, C or
x86_64 assembly. The design is specified in [`../Jobs.md`](../Jobs.md).

```
[ Python source ]
        │
        ▼
   ┌──────────┐  ◄── rules/frontends/python.json
   │ Frontend │        (Python AST → Canonical IR)
   └────┬─────┘
        ▼
   ┌───────────┐  ◄── core/ir.py          (structural contract)
   │ Canonical │  ◄── core/type_checker.py (types, validation, hoisting)
   │    IR     │
   └────┬──────┘
        ▼
   ┌──────────┐  ◄── rules/backends/<target>.json
   │ Backend  │        (IR → target code)
   └────┬─────┘
        ▼
[ Rust | Ruby | C | x86_64 assembly ]
```

The guiding principle: **language/target knowledge lives in JSON rule files, not
in Python**. Adding a block-structured target means adding one file under
`rules/backends/`.

## Repository layout

```
.
├── README.md                     # overview, usage, limitations
├── Jobs.md                       # original specification (source of truth)
├── docs/
│   ├── ARCHITECTURE.md           # this file
│   └── DEVELOPMENT.md            # workflow + roadmap
└── pytranspiler/                 # the project (also importable as a package)
    ├── pytranspiler.py           # CLI entrypoint + `Transpiler` orchestrator
    ├── core/
    │   ├── parser.py             # Python AST → Canonical IR (data-driven)
    │   ├── ir.py                 # IR node constructors + structural validation
    │   ├── type_checker.py       # type inference, validation, variable hoisting
    │   ├── emitter.py            # generic template engine + x86_64 code generator
    │   └── schema.py             # dependency-free JSON-Schema validator
    ├── rules/
    │   ├── frontends/python.json # Python AST → IR operator/type mapping
    │   └── backends/
    │       ├── rust.json         # literal backend
    │       ├── ruby.json         # literal backend
    │       ├── c.json            # literal backend (Phase 5 extensibility proof)
    │       └── x86_64.json       # assembly backend (System V, NASM syntax)
    ├── schemas/
    │   ├── frontend.schema.json  # JSON-Schema for rules/frontends/*
    │   ├── backend.schema.json   # JSON-Schema for rules/backends/*
    │   └── ir.schema.json        # JSON-Schema for a Canonical IR module
    └── tests/
        ├── run_tests.py          # validation harness (snapshots + native run)
        └── cases/
            ├── *.py              # input programs
            └── expected/         # golden output per case × target
```

## Pipeline stages

Orchestrated by `Transpiler.build_ir` / `Transpiler.transpile` in
`pytranspiler/pytranspiler.py`:

| # | Stage | Code | Reads | Produces |
|---|---|---|---|---|
| 1 | Parse & lower | `core/parser.py` | source + `rules/frontends/python.json` | Canonical IR module |
| 2 | Validate IR | `core/ir.py: validate` | IR | `IRValidationError` on violation |
| 3 | Type resolve | `core/type_checker.py` | IR + frontend rules | typed IR (`type`, `decl`, `mutable`, `locals`) |
| 4 | Emit | `core/emitter.py: create_emitter` | typed IR + `rules/backends/<target>.json` | target source text |
| 5 | Write | CLI | text | file / stdout |

Stages 1–3 are **frontend/target agnostic**; only the IR crosses the boundary, so
backends can in principle be driven from a stored IR (see `--dump-ir`).

## The Canonical IR

Defined and validated in `core/ir.py`. A module is a plain dict:

```json
{ "unit": "module", "body": [ <node>, ... ] }
```

**Node kinds** (`ir.ALL_KINDS`):

| Category | Kinds |
|---|---|
| Statements | `FunctionDef`, `Return`, `Assign`, `If`, `While`, `Call` |
| Expressions | `BinOp`, `UnaryOp`, `Compare`, `Call`, `Var`, `Literal` |

**Type vocabulary** (`ir.KNOWN_TYPES`): `i64`, `f64`, `bool`, `str`, `void`.
Numerics are promoted via `ir.NUMERIC_ORDER` (`bool < i64 < f64`).

### Annotations added by the type checker

`core/type_checker.py` mutates the IR in place, filling in derived fields. Every
back-end may rely on these:

| Node | Field | Meaning |
|---|---|---|
| `FunctionDef` | `return_type` | inferred when not annotated |
| `FunctionDef` | `params[i].mutable` | parameter is reassigned in the body |
| `FunctionDef` | `locals` | **hoisted** locals: `[{name, type, mutable}]` in first-appearance order |
| `Assign` | `decl` | this is the first binding visible at that point |
| `Assign` | `mutable` | assigned ≥ 2 times (needs `mut` in Rust) |
| `Assign`/`Var`/`Literal`/`BinOp`/`UnaryOp`/`Compare`/`Call` | `type` | resolved neutral type |

`type_checker.py` is also where **semantic validation** lives: undefined
variables, ill-typed operators, incompatible annotated/inferred types, and
conflicting types for one local all raise `TypeCheckError`.

### Variable hoisting

Python scopes variables to the function, targets like Rust/C to the block. To
reconcile them, the type checker collects every non-parameter local in
first-appearance order, unifies the types of all of its assignments (widening
numerics, rejecting genuine conflicts), and records `FunctionDef.locals`.
Backends that set `"hoist_locals": true` declare them once in the prologue and
treat every assignment as a reassignment. See README → *Design hardening §1*.

## Rule files

### Frontend — `rules/frontends/python.json`

Validated against `schemas/frontend.schema.json`. Keys: `binop_ops`,
`unary_ops`, `compare_ops`, `type_hints`, `literal_types`,
`builtin_return_types`. Python AST operator classes map to the neutral
mnemonics the IR and backends agree on (`ADD`, `SUB`, `EQ`, …).

`core/parser.py` is the *only* Python-specific code: it walks the AST and looks
up the mappings from this file. That is why operator coverage can change
without touching Python.

### Backend — `rules/backends/<target>.json`

Validated against `schemas/backend.schema.json` (Phase 5). Common keys:

| Key | Purpose |
|---|---|
| `target`, `description`, `mode` | identity; `mode` is `literal` or `assembly` |
| `extension`, `header`, `footer` | output file wrapping |
| `hoist_locals` | emit `FunctionDef.locals` as a prologue |
| `indent_unit`, `statement_suffix` | literal-backend formatting |
| `types` | neutral type → target type (`i64` → `long`, …) |
| `templates` | node kind → template string |
| `operators`, `unary_operators`, `compare_operators` | mnemonic → target token |
| `builtins` | IR `Call` function name → target call snippet |
| `boolean`, `string`, `null` | literal rendering |

Assembly-only keys (read by `AsmEmitter`): `abi`, `syntax`, `arg_registers`,
`accumulator`, `scratch_register`, `base_pointer`, `stack_pointer`, `word_size`,
`stack_alignment`, `memory_sizes`, `compare_setcc`.

#### Template placeholders

`Emitter._resolve` understands: `{indent}` `{body}` `{locals}` `{orelse}`
`{params}` `{args}` `{op}` `{let_kw}` `{mut}` `{type}` `{return_type}`
`{value}` `{left}` `{right}` `{test}` `{operand}` `{name}` `{target}` `{func}`,
plus a fallback to any scalar key of the current node. Unknown placeholders
raise `EmitterError`.

#### Template names looked up

`FunctionDef`, `Param`, `Local`, `Return`, `Assign`, `Reassign`, `If`, `Elif`,
`Else`, `While`, `Call`, `BinOp` (or `BinOp_<OP>` for a per-operator override),
`UnaryOp`, `Compare`, `Var`, `Literal`.

## The two emitter strategies

`core/emitter.py` contains two classes, chosen by `create_emitter(backend, frontend)`:

**`Emitter`** — a generic recursive template engine for block-structured
targets (Rust, Ruby, C). It renders node kind → template, resolving
placeholders recursively. Beyond that it only decides formatting: the
`hoist_locals` prologue, the `Assign`/`Reassign` split, `elif`/`else` chaining,
and block indentation.

**`AsmEmitter`** — the x86_64 code generator. Templates cannot express register
allocation and labels, so it is written in Python but still reads its registers,
mnemonics, frame sizes and function prologue/epilogue from
`rules/backends/x86_64.json`. Key mechanics:

- functions are emitted sorted by name for deterministic output;
- each function reserves `[rbp-8] … [rbp-N]` for parameters + hoisted locals and
  allocates `sub rsp, align(N*8, stack_alignment)` (16 bytes, System V);
- register parameters are copied from `arg_registers` into their slots;
- expressions are evaluated with a **stack-based accumulator**: the left operand
  is `push`ed, the right operand is computed into the accumulator (`rax`), and
  the operation pops it back through the scratch register (`r11`); register
  pressure is constant regardless of nesting depth;
- labels are namespaced per function: `.L_<fn>_<prefix>_<n>` plus
  `.L_end_<fn>` for the shared epilogue;
- unsupported nodes (floats, calls, `and`/`or` on integers, > 6 parameters) fail
  fast with a descriptive `EmitterError`.

## Testing architecture

`tests/run_tests.py` is the single entrypoint and is deliberately
artifact-oriented:

1. **Snapshots** — output for every case × target vs `tests/cases/expected/`.
2. **Native execution** — generated x86_64 is translated to GAS Intel syntax,
   assembled and linked against a generated C driver; generated C is compiled
   directly. Both are **run**, and results are compared against the original
   Python functions.
3. **Negative cases** — undefined variables, type errors, unsupported syntax,
   conflicting local types.
4. **Schema validation** — every file under `rules/`.
5. **IR contract** — shape checks plus a deliberately malformed node.
6. **Extensibility** — the C target is discovered from `rules/` alone.

`SAMPLES` in the harness supplies deterministic arguments per arity; the default
for an unlisted arity is `tuple(range(n))`.

## Constraints on the design

- **Standard library only.** No third-party runtime dependencies; `schema.py`
  implements the JSON-Schema subset the project uses.
- **Deterministic output.** Same input ⇒ byte-identical output (hence the
  name-sorted functions in `AsmEmitter` and golden snapshots).
- **Verify by running.** A successful transpile is not proof; generated C and
  assembly must compile *and* produce correct values.
