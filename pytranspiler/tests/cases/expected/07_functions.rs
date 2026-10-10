pub fn square(x: i64) -> i64 {
    return (x * x);
}

pub fn add(a: i64, b: i64) -> i64 {
    return (a + b);
}

pub fn sum_of_squares(a: i64, b: i64) -> i64 {
    return add(square(a), square(b));
}

pub fn factorial(n: i64) -> i64 {
    if (n <= 1) {
        return 1;
    } else {
        return (n * factorial((n - 1)));
    }
}
