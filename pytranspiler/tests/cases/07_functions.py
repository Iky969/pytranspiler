def square(x: int) -> int:
    return x * x


def add(a: int, b: int) -> int:
    return a + b


def sum_of_squares(a: int, b: int) -> int:
    return add(square(a), square(b))


def factorial(n: int) -> int:
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)
