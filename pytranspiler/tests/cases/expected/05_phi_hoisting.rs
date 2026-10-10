pub fn choose(flag: i64) -> i64 {
    let mut x: i64;
    if (flag > 0) {
        x = 10;
    } else {
        x = 20;
    }
    return x;
}

pub fn clamp(value: i64, high: i64) -> i64 {
    let mut result: i64;
    if (value > high) {
        result = high;
    } else {
        result = value;
    }
    return result;
}

pub fn branch_then_loop(n: i64) -> i64 {
    let mut total: i64;
    if (n > 0) {
        total = n;
    } else {
        total = 0;
    }
    while (total > 0) {
        total = (total - 1);
    }
    return total;
}
