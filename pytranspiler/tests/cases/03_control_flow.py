def max_of(a: int, b: int) -> int:
    if a > b:
        return a
    else:
        return b


def sign(x: int) -> int:
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0


def sum_to(n: int) -> int:
    total = 0
    i = n
    while i > 0:
        total = total + i
        i = i - 1
    return total
