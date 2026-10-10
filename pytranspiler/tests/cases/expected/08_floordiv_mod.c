#include <stdbool.h>

long floor_div_pos(long a, long b) {
    return (((a) / (b)) - (((a) % (b) != 0 && ((a) ^ (b)) < 0) ? 1 : 0));
}

long mod_pos(long a, long b) {
    return (((a) % (b)) + ((b) * ((((a) % (b) != 0 && ((a) ^ (b)) < 0) ? 1 : 0))));
}

long floor_div_neg(long a, long b) {
    return ((((-a)) / (b)) - ((((-a)) % (b) != 0 && (((-a)) ^ (b)) < 0) ? 1 : 0));
}

long mod_neg(long a, long b) {
    return ((((-a)) % (b)) + ((b) * (((((-a)) % (b) != 0 && (((-a)) ^ (b)) < 0) ? 1 : 0))));
}

long combined(long a, long b) {
    long q;
    long r;
    q = (((a) / (b)) - (((a) % (b) != 0 && ((a) ^ (b)) < 0) ? 1 : 0));
    r = (((a) % (b)) + ((b) * ((((a) % (b) != 0 && ((a) ^ (b)) < 0) ? 1 : 0))));
    return ((q * b) + r);
}
