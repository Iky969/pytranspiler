def fibonacci(n: int) -> int:
    """Return the n-th Fibonacci number (iterative)."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        a = 0
        b = 1
        i = 2
        while i <= n:
            temp = a + b
            a = b
            b = temp
            i = i + 1
        return b
