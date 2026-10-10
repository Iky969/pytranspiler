def collatz_steps(n: int) -> int:
    """Count the number of steps to reach 1 in the Collatz sequence."""
    steps = 0
    while n > 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = n * 3 + 1
        steps = steps + 1
    return steps
