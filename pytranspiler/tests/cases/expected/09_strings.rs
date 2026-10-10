pub fn concat(a: String, b: String) -> String {
    return format!("{}{}", a, b);
}

pub fn greet(name: String) -> String {
    return format!("{}{}", format!("{}{}", "hello, ", name), "!");
}
