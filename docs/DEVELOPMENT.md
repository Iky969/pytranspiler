# Development guide & roadmap

How to work on `pytranspiler`, extend it, and where it should go next.
Read [`ARCHITECTURE.md`](./ARCHITECTURE.md) first for the pipeline and data
contracts.

## Ground rules

1. **Standard library only.** No third-party runtime dependencies. If you need
   a capability (e.g. schema validation), implement the minimal subset needed,
   as `core/schema.py` does.
2. **Target knowledge belongs in JSON.** Prefer extending
   `rules/backends/<target>.json` over adding branches to Python. Reach for
   Python only for things templates genuinely cannot express (register
   allocation, label generation).
3. **Deterministic output.** Same input ⇒ byte-identical output. Keep golden
   snapshots meaningful; never sort by `dict` iteration order.
4. **Verify by running.** Snapshots prove *stability*, not *correctness*.
   Generated C and assembly must be compiled and executed, and the runtime
   result compared against the Python original.
5. **Fail loudly.** Unsupported constructs raise a specific error
   (`FrontendError`, `TypeCheckError`, `IRValidationError`, `EmitterError`)
   rather than emitting wrong code.

## Environment & commands

CPython 3.8+ is required (the code relies on `ast.Constant`, which the parser
returns from 3.8 onwards). It is developed and verified on 3.10 and uses only
the standard library, so there is nothing to install.

```bash
cd pytranspiler

# validate the rule files against schemas/
python3 pytranspiler.py --check-rules

# list targets / transpile
python3 pytranspiler.py --list-targets
python3 pytranspiler.py tests/cases/03_control_flow.py -t rust -o -
python3 pytranspiler.py tests/cases/03_control_flow.py -t x86_64 -o control.asm

# inspect the typed IR (includes hoisted `locals`)
python3 pytranspiler.py tests/cases/05_phi_hoisting.py --dump-ir

# test harness
python3 tests/run_tests.py            # check
python3 tests/run_tests.py --update   # regenerate golden snapshots
```

`gcc` is required for the native-execution checks. If it is missing those
checks report `SKIP` (they never silently pass). `rustc` and `ruby` are not used
by the harness.

## Extension recipes

### 1. Add a block-structured target (e.g. Go, TypeScript)

JSON only — this is the Phase 5 promise.

1. Create `rules/backends/<name>.json` with `target`, `mode: "literal"`,
   `extension`, `types`, `templates` (at least `FunctionDef`, `Param`,
   `Return`, `Assign`, `Reassign`, `If`, `While`, `BinOp`, `Compare`, `Var`,
   `Literal`), `operators`, `unary_operators`, `compare_operators`.
2. Add `"hoist_locals": true` and a `Local` template if the target has block
   scope (declarations must move to the prologue — see ARCHITECTURE → hoisting).
3. If the target needs declarations elsewhere (a `#include`, a `module` line),
   use `header` / `footer`.
4. Run `python3 pytranspiler.py --check-rules` — the schema validates it.
5. Add the new target to `CASE_TARGETS` in `tests/run_tests.py`, then
   `python3 tests/run_tests.py --update` and review the new golden files by hand
   before trusting them.

### 2. Add a new IR node

An IR node touches several files; do them in this order:

1. `core/ir.py` — add the kind constant to `STATEMENT_KINDS`/`EXPRESSION_KINDS`,
   a constructor, an entry in `_REQUIRED_KEYS`, `iter_child_expressions` and
   (if it nests statements) `walk`.
2. `schemas/ir.schema.json` — mirror the new shape.
3. `core/parser.py` — lower the Python AST node that produces it.
4. `core/type_checker.py` — add inference/validation in `_check_stmt`/`_infer`
   and, if it introduces bindings, teach `_count_assigns`/`_collect_locals`.
5. `rules/backends/*.json` — add a template for every target.
6. `core/emitter.py` — only if the node needs codegen logic (`AsmEmitter`);
   otherwise a template suffices.
7. `tests/` — add a case and negative coverage.

### 3. Add a case or a builtin

- **Case**: drop a `<NN>_name.py` under `tests/cases/`, register it in
  `CASE_TARGETS` (and `SAMPLES` if you need specific arguments), then
  `--update`. If the file has no `x86_64` snapshot, say why in the comment.
- **Builtin**: add the name to `builtin_return_types` in
  `rules/frontends/python.json` (so the type checker accepts it) and to
  `builtins` in each backend that can express it. Backends without an entry
  fall back to the generic `Call` template or fail with `EmitterError`.

## Roadmap

Ordered by value-to-effort. Each item names the files to touch and how to prove
it works — turn the proof into a harness check so it stays true.

### Track 1 — Semantics correctness (highest value)

These are *verified* divergences from Python today, not hypotheticals:

| Gap | Python | Emitted C/x86_64 | Where |
|---|---|---|---|
| Floor division | `-7 // 3 == -3` | `-2` (truncates toward zero) | `core/type_checker.py: _binop_type`, `core/emitter.py: _emit_binop` |
| Modulo sign | `-7 % 3 == 2` | `-1` (sign follows dividend) | same |
| User function calls | works | `TypeCheckError: call to unknown function` | `core/type_checker.py: _infer` (`CALL`) |

- **Floor division / modulo**: post-adjust the `idiv` result (or emit a helper)
  so integer `//` and `%` match Python for negative operands. Add a case with
  negative operands and assert the runtime value — the existing harness would
  catch a regression automatically once the case exists.
- **User function calls**: collect a symbol table of top-level `FunctionDef`
  signatures in the type checker, type-check calls against it, and emit real
  calls in `AsmEmitter` (see Track 2 — this needs ABI work).
- **Definite initialization**: a local assigned on only one branch and read
  afterwards is currently rejected by the *target* compiler with a confusing
  message. Either reject it in `_collect_locals` with a precise
  `TypeCheckError`, or synthesize a zero initializer. Document the choice.
- **Division by zero**: define behaviour (compile-time constant check, or a
  runtime trap) and document it.
- **Short-circuit boolean**: `and`/`or` lower to `&&`/`||` in Rust/C (fine) but
  `AsmEmitter` rejects them. If evaluating both sides is acceptable, emit
  `and`/`or`; if not, emit branchy code.

### Track 2 — x86_64 backend depth

- **Floating point** (SSE2): `float` currently raises. Use `xmm0…` with
  `movsd`/`addsd`/`mulsd`/`divsd`, and a parallel `f64` value class; the
  `memory_sizes` entry for `f64` already exists. Add direct-double argument
  passing (`xmm0…xmm7`) and return in `xmm0`.
- **Function calls**: required for `print`/`printf` and user calls. Needs
  (a) maintaining 16-byte `rsp` alignment *at the `call`*, (b) the SysV
  variadic convention (`al` = number of vector registers) for `printf`,
  (c) spilling more than six arguments to the stack, (d) preserving
  callee-saved registers. `stack_alignment` and `_align_frame` are the
  starting point.
- **Register allocation**: replace the `push`/`pop` spills with a simple
  graph-colouring or linear-scan allocator over the existing `[rbp-N]` slots.
  Measure instruction count before/after.
- **Strings & read-only data**: add a `.rodata` section with a literal pool and
  pass `lea rdi, [rel .LC0]` to `printf`.
- **More than six parameters**: currently an error; spill to the incoming stack
  area.

### Track 3 — Language coverage

- **`for` loops**: lower `for i in range(n)` to `While` + an induction variable
  in `core/parser.py` (keeps every backend unchanged).
- **`break` / `continue`**: new IR nodes with a loop-stack in `AsmEmitter`
  (labels already exist) and templates for literal backends.
- **Compound data**: `List`/`array` types with indexing and `len`; then
  tuples/structs. Requires new `KNOWN_TYPES` entries and `memory_sizes`.
- **String operations**: `str` currently types but is not really usable on C
  (`char *`) or x86_64. Decide on a representation before adding operations.
- **Narrower integers & casts**: `i32`/`u8` plus explicit conversions, so the
  overflow range is expressible per variable.

### Track 4 — Architecture & extensibility

- **Pluggable frontends.** `core/parser.py` is the only Python-specific stage
  and there is no registry. Introduce `core/frontends/` with a `Frontend`
  protocol, a registry keyed by `rules/frontends/*.json: language`, and move the
  Python lowering into `core/frontends/python.py`. Then a C/Go subset can be
  added as a new module + rule file.
- **IR as a public interface.** Add `--emit-ir <file>` / `--ir-in <file>` so a
  backend can be driven from stored IR, fully decoupling front from back end.
  This is what makes third-party backends possible.
- **Backend capability declaration.** Add a `supports: {floats, calls, strings,
  break, …}` block to `rules/backends/*.json`, validate it in
  `schemas/backend.schema.json`, and fail early with a clear message instead of
  discovering the limitation mid-emit.
- **Diagnostics with positions.** The parser has `node.lineno` but the type
  checker drops it. Thread source spans through the IR and render
  `file:line:col` errors.

### Track 5 — Tooling, packaging, CI

- **Packaging**: add `pyproject.toml` with a `pytranspiler` console script and
  make `core` an importable package (`pytranspiler/core/...` or a
  `pytranspiler/__init__.py` at the project root) so it can be installed.
- **CI**: a GitHub Actions workflow that runs `--check-rules` and
  `tests/run_tests.py` on Linux with `gcc` present (so native checks run, not
  skip), plus `python3 -m compileall`.
- **Static checks**: run `mypy`/`ruff` in CI; the code already uses type hints
  throughout.
- **CLI UX**: multiple input files, `--watch`, `-o <dir>`, and a
  `--targets` capability listing.

### Track 6 — Performance

- **IR-level constant folding** before emission (a new pass next to the type
  checker) — shrinks output and removes obvious dead arithmetic.
- **Dead code elimination** for unreachable branches after folding.
- **Peephole** on the assembly (e.g. collapse `mov rax, X` + `push rax` into
  `push X`).
- **Measurement**: record generated instruction count per case in the harness so
  optimisation work has a real number to move, rather than a claim.

## Definition of done

Before considering a change complete:

- [ ] `python3 pytranspiler.py --check-rules` exits 0.
- [ ] `python3 tests/run_tests.py` exits 0 with **0 failed and 0 unexpected
      skips**; if `gcc` is available, no native check may be skipped.
- [ ] New/changed generated code for a *runnable* target is compiled and
      executed, and the value is compared to Python — not just snapshot-compared.
- [ ] New target files pass schema validation; new IR nodes are covered in
      `schemas/ir.schema.json`.
- [ ] `README.md` / `docs/` limitations and roadmap are updated if a limitation
      changed or a new one was introduced.
- [ ] Any check that could not run is reported as a limitation, never as a pass.
