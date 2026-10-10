#include <stdbool.h>

long neg_literal() {
    return (0 - 42);
}

long neg_var(long a) {
    return (0 - a);
}

long sign_flip(long a) {
    long x;
    x = a;
    x = (0 - x);
    return x;
}
