"""Backend: turn the Canonical IR into target code.

The generic :class:`Emitter` is a small recursive template engine.  It
reads a node's kind from the IR, looks up the matching template in the
selected ``rules/backends/*.json`` file and fills the ``{placeholders}``
recursively.  Because every target is described by data, adding a new
block-structured target only requires a new JSON file -- no Python changes.

The x86_64 target is different in kind: it needs register allocation and
label generation, so it is implemented by :class:`AsmEmitter`, which still
reads its registers, operator mnemonics and prologue/epilogue template from
``rules/backends/x86_64.json``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from . import ir

_PLACEHOLDER = re.compile(r"\{(\w+)\}")


class EmitterError(NotImplementedError):
    """Raised when a backend has no rule for a node in the IR."""


class Emitter:
    """Generic, template-driven backend emitter."""

    def __init__(self, backend: Dict[str, Any], frontend: Dict[str, Any]):
        self.backend = backend
        self.frontend = frontend
        self.templates: Dict[str, str] = backend.get("templates", {})
        self.operators: Dict[str, str] = backend.get("operators", {})
        self.unary_operators: Dict[str, str] = backend.get("unary_operators", {})
        self.compare_operators: Dict[str, str] = backend.get("compare_operators", {})
        self.types: Dict[str, str] = backend.get("types", {})
        self.builtins: Dict[str, str] = backend.get("builtins", {})
        self.boolean: Dict[str, str] = backend.get("boolean", {"true": "true", "false": "false"})
        self.string: Dict[str, str] = backend.get("string", {"quote": '"'})
        self.indent_unit: str = backend.get("indent_unit", "    ")
        self.header: str = backend.get("header", "")
        self.footer: str = backend.get("footer", "")

    # -- public API ---------------------------------------------------------

    def emit_module(self, module_ir: Dict[str, Any]) -> str:
        parts = [self.emit_statement(node, 0) for node in module_ir["body"]]
        text = "\n\n".join(parts)
        if self.header:
            text = self.header + text
        if self.footer:
            text = text + self.footer
        return text + "\n"

    def emit(self, node: Dict[str, Any], indent: int) -> str:
        kind = node["node"]
        if kind == ir.BIN_OP:
            template = self.templates.get("BinOp_" + node["op"]) or self.templates.get(ir.BIN_OP)
        elif kind == ir.CALL:
            template = self.builtins.get(node["func"]) or self.templates.get(ir.CALL)
        elif kind == ir.ASSIGN and not node.get("decl", True):
            template = self.templates.get("Reassign") or self.templates.get(ir.ASSIGN)
        else:
            template = self.templates.get(kind)
        if template is None:
            raise EmitterError(f"target '{self.backend.get('target')}' has no template for {kind}")
        return self._render(template, node, indent)

    # -- template engine ----------------------------------------------------

    def _render(self, template: str, node: Dict[str, Any], indent: int) -> str:
        return _PLACEHOLDER.sub(lambda m: self._resolve(m.group(1), node, indent), template)

    def _resolve(self, key: str, node: Dict[str, Any], indent: int) -> str:
        kind = node.get("node")
        if key == "indent":
            return self.indent_unit * indent
        if key == "body":
            return self._render_body(node.get("body", []), indent + 1)
        if key == "orelse":
            return self._render_orelse(node, indent)
        if key == "params":
            param_tmpl = self.templates.get("Param", "{name}")
            return ", ".join(self._render(param_tmpl, p, indent) for p in node.get("params", []))
        if key == "args":
            return ", ".join(self.emit(a, indent) for a in node.get("args", []))
        if key == "op":
            return self._operator(node)
        if key == "let_kw":
            return "let mut " if node.get("mutable") else "let "
        if key == "mut":
            return "mut " if node.get("mutable") else ""
        if key == "type":
            return self._type_name(node.get("type"))
        if key == "return_type":
            return self._type_name(node.get("return_type"))
        if key == "value":
            if kind == ir.LITERAL:
                return self._literal(node["value"])
            value = node.get("value")
            return self.emit(value, indent) if value is not None else ""
        if key in ("left", "right", "test", "operand"):
            return self.emit(node[key], indent)
        if key in ("name", "target", "func"):
            return str(node[key])
        if key in node and not isinstance(node[key], (dict, list)):
            return str(node[key])
        raise EmitterError(f"cannot resolve placeholder '{{{key}}}' for node {kind}")

    def _render_body(self, body: List[Dict[str, Any]], indent: int) -> str:
        return "\n".join(self.emit_statement(stmt, indent) for stmt in body)

    def emit_statement(self, stmt: Dict[str, Any], indent: int) -> str:
        """Emit a statement, adding block indentation and a terminator to
        bare expression statements (e.g. a ``print`` call)."""
        text = self.emit(stmt, indent)
        if stmt.get("node") == ir.CALL:
            suffix = self.backend.get("statement_suffix", "")
            return self.indent_unit * indent + text + suffix
        return text

    def _render_orelse(self, node: Dict[str, Any], indent: int) -> str:
        orelse = node.get("orelse") or []
        if not orelse:
            return ""
        if len(orelse) == 1 and orelse[0].get("node") == ir.IF:
            return self._render(self.templates["Elif"], orelse[0], indent)
        body = self._render_body(orelse, indent + 1)
        return self.templates["Else"].replace("{indent}", self.indent_unit * indent).replace(
            "{body}", body
        )

    # -- helpers ------------------------------------------------------------

    def _operator(self, node: Dict[str, Any]) -> str:
        kind = node["node"]
        if kind == ir.BIN_OP:
            table, op = self.operators, node["op"]
        elif kind == ir.UNARY_OP:
            table, op = self.unary_operators, node["op"]
        elif kind == ir.COMPARE:
            table, op = self.compare_operators, node["op"]
        else:  # pragma: no cover - defensive
            raise EmitterError(f"no operator table for node {kind}")
        if op not in table:
            raise EmitterError(f"target '{self.backend.get('target')}' has no operator for {op}")
        return table[op]

    def _type_name(self, type_: Any) -> str:
        if type_ is None:
            return ""
        return self.types.get(type_, type_)

    def _literal(self, value: Any) -> str:
        if isinstance(value, bool):
            return self.boolean["true" if value else "false"]
        if isinstance(value, str):
            quote = self.string.get("quote", '"')
            return quote + value.replace(quote, "\\" + quote) + quote
        if isinstance(value, float):
            return repr(value)
        if value is None:
            return self.backend.get("null", "None")
        return str(value)


class AsmEmitter(Emitter):
    """x86_64 (System V, NASM syntax) code generator.

    Uses a simple two-register accumulator model: sub-expressions are
    evaluated into ``rax`` and nested left-hand sides are spilled to the
    machine stack with ``push``/``pop``.  Every function reserves a frame
    large enough for its parameters and local variables; all variables live
    in ``[rbp - offset]`` slots.
    """

    def __init__(self, backend: Dict[str, Any], frontend: Dict[str, Any]):
        super().__init__(backend, frontend)
        self.arg_registers: List[str] = backend["arg_registers"]
        self.acc: str = backend.get("accumulator", "rax")
        self.scratch: str = backend.get("scratch_register", "r11")
        self.bp: str = backend.get("base_pointer", "rbp")
        self.sp: str = backend.get("stack_pointer", "rsp")
        self.word: int = backend.get("word_size", 8)
        self.alignment: int = backend.get("stack_alignment", 16)
        self.memory_sizes: Dict[str, str] = backend.get("memory_sizes", {})
        self.setcc: Dict[str, str] = backend.get("compare_setcc", {})

        # Per-function state.
        self._slots: Dict[str, int] = {}
        self._end_label = ""
        self._fn_name = ""
        self._label_counter = 0

    # -- module / function --------------------------------------------------

    def emit_module(self, module_ir: Dict[str, Any]) -> str:
        functions = [n for n in module_ir["body"] if n.get("node") == ir.FUNCTION_DEF]
        functions.sort(key=lambda n: n["name"])  # stable, deterministic output
        bodies = [self.emit_function(fn) for fn in functions]
        return "\n\n".join(bodies) + "\n"

    def emit_function(self, fn: Dict[str, Any]) -> str:
        self._slots = {}
        self._label_counter = 0
        self._fn_name = fn["name"]
        self._end_label = f".L_end_{fn['name']}"

        params = [p["name"] for p in fn["params"]]
        locals_ = [name for name in self._collect_locals(fn["body"]) if name not in params]
        order = params + locals_
        for index, name in enumerate(order):
            self._slots[name] = (index + 1) * self.word

        frame_lines: List[str] = []
        if order:
            frame_size = self._align_frame(len(order) * self.word)
            frame_lines.append(f"    sub {self.sp}, {frame_size}")
            for index, p in enumerate(fn["params"]):
                if index >= len(self.arg_registers):
                    raise EmitterError(
                        f"function '{fn['name']}' has more than {len(self.arg_registers)} "
                        "parameters; the x86_64 backend does not spill register arguments"
                    )
                frame_lines.append(
                    f"    mov {self._mem(self._slots[p['name']], p.get('type'))}, "
                    f"{self.arg_registers[index]}"
                )
        frame = ("\n".join(frame_lines) + "\n") if frame_lines else ""

        body = self._emit_body(fn["body"])
        return (
            self.templates["FunctionDef"]
            .replace("{name}", fn["name"])
            .replace("{frame}", frame)
            .replace("{body}", body)
            .replace("{end_label}", self._end_label)
        )

    # -- statements ---------------------------------------------------------

    def _emit_body(self, body: List[Dict[str, Any]]) -> str:
        return "\n".join(self._emit_stmt(stmt) for stmt in body)

    def _emit_stmt(self, stmt: Dict[str, Any]) -> str:
        kind = stmt["node"]
        if kind == ir.RETURN:
            lines = self._emit_expr(stmt["value"]) if stmt.get("value") is not None else []
            lines.append(f"    jmp {self._end_label}")
            return "\n".join(lines)
        if kind == ir.ASSIGN:
            lines = self._emit_expr(stmt["value"])
            lines.append(f"    mov {self._mem(self._slot(stmt['target']), stmt.get('type'))}, {self.acc}")
            return "\n".join(lines)
        if kind == ir.IF:
            return self._emit_if(stmt)
        if kind == ir.WHILE:
            return self._emit_while(stmt)
        if kind == ir.CALL:
            raise EmitterError(
                f"the x86_64 backend does not support calls (got '{stmt.get('func')}')"
            )
        raise EmitterError(f"the x86_64 backend does not support statement {kind}")

    def _emit_if(self, stmt: Dict[str, Any]) -> str:
        label = self._new_label("if")
        lines = self._emit_expr(stmt["test"])
        lines.append(f"    cmp {self.acc}, 0")
        if stmt.get("orelse"):
            lines.append(f"    je .L_else_{label}")
            lines.append(self._emit_body(stmt["body"]))
            if not self._terminates(stmt["body"]):
                lines.append(f"    jmp .L_end_{label}")
            lines.append(f".L_else_{label}:")
            lines.append(self._emit_body(stmt["orelse"]))
        else:
            lines.append(f"    je .L_end_{label}")
            lines.append(self._emit_body(stmt["body"]))
        lines.append(f".L_end_{label}:")
        return "\n".join(lines)

    def _terminates(self, body: List[Dict[str, Any]]) -> bool:
        """True if control can never fall out of *body* (it ends in a return)."""
        if not body:
            return False
        last = body[-1]
        if last.get("node") == ir.RETURN:
            return True
        if last.get("node") == ir.IF:
            return self._terminates(last["body"]) and self._terminates(last.get("orelse", []))
        return False

    def _emit_while(self, stmt: Dict[str, Any]) -> str:
        label = self._new_label("while")
        lines = [f".L_start_{label}:"]
        lines.extend(self._emit_expr(stmt["test"]))
        lines.append(f"    cmp {self.acc}, 0")
        lines.append(f"    je .L_end_{label}")
        lines.append(self._emit_body(stmt["body"]))
        lines.append(f"    jmp .L_start_{label}")
        lines.append(f".L_end_{label}:")
        return "\n".join(lines)

    # -- expressions (result always ends up in the accumulator) -------------

    def _emit_expr(self, node: Dict[str, Any]) -> List[str]:
        kind = node["node"]
        if kind == ir.LITERAL:
            return self._lit_lines(node["value"])
        if kind == ir.VAR:
            return [f"    mov {self.acc}, {self._mem(self._slot(node['name']), node.get('type'))}"]
        if kind == ir.BIN_OP:
            return self._emit_binop(node)
        if kind == ir.UNARY_OP:
            return self._emit_unary(node)
        if kind == ir.COMPARE:
            return self._emit_compare(node)
        if kind == ir.CALL:
            raise EmitterError(
                f"the x86_64 backend does not support calls (got '{node.get('func')}')"
            )
        raise EmitterError(f"the x86_64 backend does not support expression {kind}")

    def _emit_binop(self, node: Dict[str, Any]) -> List[str]:
        op = node["op"]
        if op in ("AND", "OR"):
            raise EmitterError(f"the x86_64 backend does not support logical '{op}' on integers")
        if op not in self.operators:
            raise EmitterError(f"the x86_64 backend has no operator for {op}")
        lines = self._emit_expr(node["left"])
        lines.append(f"    push {self.acc}")
        lines.extend(self._emit_expr(node["right"]))
        lines.append(f"    mov {self.scratch}, {self.acc}")
        lines.append(f"    pop {self.acc}")
        mnemonic = self.operators[op]
        if op in ("DIV", "FLOORDIV"):
            lines.append("    cqo")
            lines.append(f"    {mnemonic} {self.scratch}")
        elif op == "MOD":
            lines.append("    cqo")
            lines.append(f"    {mnemonic} {self.scratch}")
            lines.append(f"    mov {self.acc}, rdx")
        else:
            lines.append(f"    {mnemonic} {self.acc}, {self.scratch}")
        return lines

    def _emit_unary(self, node: Dict[str, Any]) -> List[str]:
        op = node["op"]
        lines = self._emit_expr(node["operand"])
        if op == "NOT":
            lines.append(f"    cmp {self.acc}, 0")
            lines.append("    sete al")
            lines.append(f"    movzx {self.acc}, al")
        elif op == "USUB":
            lines.append(f"    neg {self.acc}")
        elif op == "UADD":
            pass
        else:
            raise EmitterError(f"the x86_64 backend has no unary operator for {op}")
        return lines

    def _emit_compare(self, node: Dict[str, Any]) -> List[str]:
        op = node["op"]
        if op not in self.setcc:
            raise EmitterError(f"the x86_64 backend has no comparison for {op}")
        lines = self._emit_expr(node["left"])
        lines.append(f"    push {self.acc}")
        lines.extend(self._emit_expr(node["right"]))
        lines.append(f"    mov {self.scratch}, {self.acc}")
        lines.append(f"    pop {self.acc}")
        lines.append(f"    cmp {self.acc}, {self.scratch}")
        lines.append(f"    {self.setcc[op]} al")
        lines.append(f"    movzx {self.acc}, al")
        return lines

    def _lit_lines(self, value: Any) -> List[str]:
        if isinstance(value, bool):
            value = 1 if value else 0
        if isinstance(value, float):
            raise EmitterError("the x86_64 backend only supports integer literals")
        return [f"    mov {self.acc}, {value}"]

    # -- helpers ------------------------------------------------------------

    def _collect_locals(self, body: List[Dict[str, Any]]) -> List[str]:
        names: List[str] = []
        for stmt in body:
            kind = stmt.get("node")
            if kind == ir.ASSIGN and stmt["target"] not in names:
                names.append(stmt["target"])
            elif kind == ir.IF:
                for name in self._collect_locals(stmt["body"]) + self._collect_locals(stmt["orelse"]):
                    if name not in names:
                        names.append(name)
            elif kind == ir.WHILE:
                for name in self._collect_locals(stmt["body"]):
                    if name not in names:
                        names.append(name)
        return names

    def _slot(self, name: str) -> int:
        if name not in self._slots:
            raise EmitterError(f"variable '{name}' has no stack slot")
        return self._slots[name]

    def _mem(self, offset: int, type_: Any) -> str:
        size = self.memory_sizes.get(type_ or "i64", "qword")
        return f"{size} [{self.bp}-{offset}]"

    def _align_frame(self, size: int) -> int:
        rem = size % self.alignment
        return size if rem == 0 else size + (self.alignment - rem)

    def _new_label(self, prefix: str) -> str:
        self._label_counter += 1
        return f"{self._fn_name}_{prefix}_{self._label_counter}"


def create_emitter(backend: Dict[str, Any], frontend: Dict[str, Any]) -> Emitter:
    """Pick the right emitter for a backend rule file."""
    if backend.get("mode") == "assembly":
        return AsmEmitter(backend, frontend)
    return Emitter(backend, frontend)
