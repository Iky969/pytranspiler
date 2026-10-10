"""Deeply nested expressions, which stress the register model.

The x86_64 backend evaluates operands with a stack-based accumulator, so
nesting depth (rather than register count) is the only limit.
"""


def combine(a: int, b: int, c: int, d: int, e: int, f: int) -> int:
    return (a + b) * (c - d) + (e * f)


def deep(a: int, b: int, c: int, d: int) -> int:
    return ((a + b) * (c + d)) - ((a - b) * (c - d))
