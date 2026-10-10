pub fn combine(a: i64, b: i64, c: i64, d: i64, e: i64, f: i64) -> i64 {
    return (((a + b) * (c - d)) + (e * f));
}

pub fn deep(a: i64, b: i64, c: i64, d: i64) -> i64 {
    return (((a + b) * (c + d)) - ((a - b) * (c - d)));
}
