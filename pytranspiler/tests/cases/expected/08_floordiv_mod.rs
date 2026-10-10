pub fn floor_div_pos(a: i64, b: i64) -> i64 {
    return ({ let __a = a; let __b = b; let __r = __a % __b; if __r != 0 && (__a ^ __b) < 0 { __a / __b - 1 } else { __a / __b } });
}

pub fn mod_pos(a: i64, b: i64) -> i64 {
    return ({ let __a = a; let __b = b; let __r = __a % __b; if __r != 0 && (__a ^ __b) < 0 { __r + __b } else { __r } });
}

pub fn floor_div_neg(a: i64, b: i64) -> i64 {
    return ({ let __a = (-a); let __b = b; let __r = __a % __b; if __r != 0 && (__a ^ __b) < 0 { __a / __b - 1 } else { __a / __b } });
}

pub fn mod_neg(a: i64, b: i64) -> i64 {
    return ({ let __a = (-a); let __b = b; let __r = __a % __b; if __r != 0 && (__a ^ __b) < 0 { __r + __b } else { __r } });
}

pub fn combined(a: i64, b: i64) -> i64 {
    let q: i64;
    let r: i64;
    q = ({ let __a = a; let __b = b; let __r = __a % __b; if __r != 0 && (__a ^ __b) < 0 { __a / __b - 1 } else { __a / __b } });
    r = ({ let __a = a; let __b = b; let __r = __a % __b; if __r != 0 && (__a ^ __b) < 0 { __r + __b } else { __r } });
    return ((q * b) + r);
}
