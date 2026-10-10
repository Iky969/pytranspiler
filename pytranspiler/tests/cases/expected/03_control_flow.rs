pub fn max_of(a: i64, b: i64) -> i64 {
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

pub fn sign(x: i64) -> i64 {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return (0 - 1);
    } else {
        return 0;
    }
}

pub fn sum_to(n: i64) -> i64 {
    let mut total: i64;
    let mut i: i64;
    total = 0;
    i = n;
    while (i > 0) {
        total = (total + i);
        i = (i - 1);
    }
    return total;
}
