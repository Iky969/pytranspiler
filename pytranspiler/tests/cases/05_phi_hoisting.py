"""Variables first bound inside a branch (the "phi-node" case).

Python scopes `x` to the whole function, so this must survive lowering to
block-scoped targets (Rust/C).  The hoisting pass declares every local in the
prologue and both branches only assign to it.
"""


def choose(flag: int) -> int:
    if flag > 0:
        x = 10
    else:
        x = 20
    return x


def clamp(value: int, high: int) -> int:
    if value > high:
        result = high
    else:
        result = value
    return result


def branch_then_loop(n: int) -> int:
    if n > 0:
        total = n
    else:
        total = 0
    while total > 0:
        total = total - 1
    return total
