pub fn neg_literal() -> i64 {
    return (0 - 42);
}

pub fn neg_var(a: i64) -> i64 {
    return (0 - a);
}

pub fn sign_flip(a: i64) -> i64 {
    let mut x: i64;
    x = a;
    x = (0 - x);
    return x;
}
