def neg_literal() -> int:
    return -42


def neg_var(a: int) -> int:
    return -a


def sign_flip(a: int) -> int:
    x = a
    x = -x
    return x