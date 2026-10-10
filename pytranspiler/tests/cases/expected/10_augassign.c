#include <stdbool.h>

long add_assign(long x, long y) {
    x = (x + y);
    return x;
}

long sub_assign(long x, long y) {
    x = (x - y);
    return x;
}

long mul_assign(long x, long y) {
    x = (x * y);
    return x;
}

long chain_assign(long a, long b, long c) {
    a = (a + b);
    a = (a * c);
    return a;
}
