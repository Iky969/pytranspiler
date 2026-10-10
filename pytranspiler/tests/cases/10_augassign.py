def add_assign(x: int, y: int) -> int:
    x += y
    return x


def sub_assign(x: int, y: int) -> int:
    x -= y
    return x


def mul_assign(x: int, y: int) -> int:
    x *= y
    return x


def chain_assign(a: int, b: int, c: int) -> int:
    a += b
    a *= c
    return a