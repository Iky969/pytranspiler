def power(base: int, exp: int) -> int:
    """Compute base^exp using repeated multiplication."""
    result = 1
    i = 0
    while i < exp:
        result = result * base
        i = i + 1
    return result
