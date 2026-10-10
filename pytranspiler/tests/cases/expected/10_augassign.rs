pub fn add_assign(mut x: i64, y: i64) -> i64 {
    x = (x + y);
    return x;
}

pub fn sub_assign(mut x: i64, y: i64) -> i64 {
    x = (x - y);
    return x;
}

pub fn mul_assign(mut x: i64, y: i64) -> i64 {
    x = (x * y);
    return x;
}

pub fn chain_assign(mut a: i64, b: i64, c: i64) -> i64 {
    a = (a + b);
    a = (a * c);
    return a;
}
