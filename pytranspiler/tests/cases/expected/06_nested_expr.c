#include <stdbool.h>

long combine(long a, long b, long c, long d, long e, long f) {
    return (((a + b) * (c - d)) + (e * f));
}

long deep(long a, long b, long c, long d) {
    return (((a + b) * (c + d)) - ((a - b) * (c - d)));
}
