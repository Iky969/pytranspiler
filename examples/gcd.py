def gcd(a: int, b: int) -> int:
    """Compute the GCD of two integers using the Euclidean algorithm."""
    if a < 0:
        a = -a
    if b < 0:
        b = -b
    while b > 0:
        temp = b
        b = a % b
        a = temp
    return a
