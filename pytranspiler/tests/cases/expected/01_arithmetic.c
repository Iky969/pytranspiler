#include <stdbool.h>

long add(long a, long b) {
    return (a + b);
}

long sub(long a, long b) {
    return (a - b);
}

long mul(long a, long b) {
    return (a * b);
}

long mix(long a, long b) {
    return (a + (b * (a - b)));
}
