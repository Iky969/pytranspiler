#include <stdbool.h>

long max_of(long a, long b) {
    if ((a > b)) {
        return a;
    } else {
        return b;
    }
}

long sign(long x) {
    if ((x > 0)) {
        return 1;
    } else if ((x < 0)) {
        return (0 - 1);
    } else {
        return 0;
    }
}

long sum_to(long n) {
    long total;
    long i;
    total = 0;
    i = n;
    while ((i > 0)) {
        total = (total + i);
        i = (i - 1);
    }
    return total;
}
