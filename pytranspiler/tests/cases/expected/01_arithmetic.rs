pub fn add(a: i64, b: i64) -> i64 {
    return (a + b);
}

pub fn sub(a: i64, b: i64) -> i64 {
    return (a - b);
}

pub fn mul(a: i64, b: i64) -> i64 {
    return (a * b);
}

pub fn mix(a: i64, b: i64) -> i64 {
    return (a + (b * (a - b)));
}
