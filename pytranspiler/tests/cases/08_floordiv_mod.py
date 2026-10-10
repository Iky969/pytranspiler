def floor_div_pos(a: int, b: int) -> int:
    return a // b


def mod_pos(a: int, b: int) -> int:
    return a % b


def floor_div_neg(a: int, b: int) -> int:
    return (-a) // b


def mod_neg(a: int, b: int) -> int:
    return (-a) % b


def combined(a: int, b: int) -> int:
    q = a // b
    r = a % b
    return q * b + r
