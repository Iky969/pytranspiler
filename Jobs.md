Arsitektur Sistem
Transpiler ini mengadopsi arsitektur modular Frontend \to Canonical IR \to Backend yang dipandu oleh file definisi aturan (supporter files).
[Source Code] 
      │
      ▼
┌─────────────┐
│  Frontend   │ ◄─── rules/frontends/<lang>.json
└──────┬──────┘
       ▼
┌─────────────┐
│ Canonical IR│ ◄─── Validasi Tipe & Normalisasi Scope
└──────┬──────┘
       ▼
┌─────────────┐
│   Backend   │ ◄─── rules/backends/<target>.json
└──────┬──────┘
       │
       ▼
[Target Output] (Assembly, Rust, Ruby)

Struktur Direktori Proyek
pytranspiler/
├── pytranspiler.py             # CLI entrypoint: parsing argumen input/output
├── core/
│   ├── parser.py               # Wrapper parser Python AST bawaan
│   ├── ir.py                   # Definisi struktur data Canonical IR
│   ├── type_checker.py         # Inferensi & validasi tipe variabel
│   └── emitter.py              # Template engine pemroses IR ke backend
├── rules/
│   ├── frontends/
│   │   └── python.json         # Aturan mapping Python AST -> IR
│   └── backends/
│       ├── x86_64.json         # Template output x86_64 NASM/GAS
│       ├── rust.json           # Template output Rust
│       └── ruby.json           # Template output Ruby
└── tests/
    └── cases/                  # File uji validasi kompilasi

Spesifikasi Kontrak Data
1. Format Canonical IR (core/ir.py)
Semua sintaks bahasa sumber dinormalisasi menjadi struktur JSON/Dictionary netral:
{
  "unit": "module",
  "body": [
    {
      "node": "FunctionDef",
      "name": "add",
      "params": [
        {"name": "a", "type": "i64"},
        {"name": "b", "type": "i64"}
      ],
      "return_type": "i64",
      "body": [
        {
          "node": "Return",
          "value": {
            "node": "BinOp",
            "op": "ADD",
            "left": {"node": "Var", "name": "a", "type": "i64"},
            "right": {"node": "Var", "name": "b", "type": "i64"}
          }
        }
      ]
    }
  ]
}

2. Format File Supporter Backend (rules/backends/*.json)
Target: Rust (rules/backends/rust.json)
{
  "types": {
    "i64": "i64",
    "f64": "f64",
    "bool": "bool"
  },
  "templates": {
    "FunctionDef": "pub fn {name}({params}) -> {return_type} {\n{body}\n}",
    "Param": "{name}: {type}",
    "Return": "    return {value};",
    "BinOp": "({left} {op} {right})",
    "Var": "{name}"
  },
  "operators": {
    "ADD": "+",
    "SUB": "-",
    "MUL": "*"
  }
}

Target: Ruby (rules/backends/ruby.json)
{
  "types": {},
  "templates": {
    "FunctionDef": "def {name}({params})\n{body}\nend",
    "Param": "{name}",
    "Return": "  return {value}",
    "BinOp": "({left} {op} {right})",
    "Var": "{name}"
  },
  "operators": {
    "ADD": "+",
    "SUB": "-",
    "MUL": "*"
  }
}

Target: Assembly x86_64 (rules/backends/x86_64.json)
{
  "abi": "SystemV",
  "arg_registers": ["rdi", "rsi", "rdx", "rcx", "r8", "r9"],
  "templates": {
    "FunctionDef": "global {name}\n{name}:\n    push rbp\n    mov rbp, rsp\n{body}\n    mov rsp, rbp\n    pop rbp\n    ret",
    "Return": "{value}",
    "BinOp_ADD": "    mov rax, {left}\n    add rax, {right}"
  }
}

Pipeline Eksekusi Per Baris Kode
 * AST Extraction: core/parser.py membaca source code Python menggunakan modul bawaan ast.parse().
 * IR Lowering: AST ditransformasi ke format Canonical IR berdasarkan definisi rules/frontends/python.json.
 * Type Resolution: core/type_checker.py mengisi atribut type yang kosong melalui propagasi tipe (contoh: literal integer \to i64).
 * Backend Matching: core/emitter.py membaca nama node dari IR, mengambil template string dari file target yang dipilih, lalu mengisi placeholder {...} secara rekursif.
 * Output Generation: Teks target diekspor ke file fisik.
Roadmap Pengembangan
| Fase | Target Milestone | Deliverable Utama | Batasan Fitur |
|---|---|---|---|
| Fase 1 | Scalar Pipeline | pytranspiler.py, ir.py, emitter.py, rust.json, ruby.json | Hanya fungsi dengan operasi aritmatika dasar +, -, literal angka, dan return. |
| Fase 2 | x86_64 Assembly Backend | rules/backends/x86_64.json, Register Allocator sederhana | Menghasilkan file assembly yang valid dirakit via NASM/GCC untuk fungsi aritmatika Fase 1. |
| Fase 3 | Type Inference & Variable | core/type_checker.py, penanganan Assign & Var deklarasi | Inferensi tipe lokal tanpa anotasi manual: x = 10 otomatis terpetakan sebagai tipe integer 64-bit. |
| Fase 4 | Control Flow | Penambahan node If, While, Compare, perbaikan generator label unik | Percabangan dan perulangan: pembuatan label .L_true_X / .L_end_X di assembly, blok indented di Rust/Ruby. |
| Fase 5 | Modular Extensibility | Validasi skema JSON via JSON-Schema untuk semua file di folder rules/ | Menambah target baru (misal C, Go) cukup menambahkan file .json baru tanpa menyentuh file Python. |
