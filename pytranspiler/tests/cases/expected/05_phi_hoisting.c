#include <stdbool.h>

long choose(long flag) {
    long x;
    if ((flag > 0)) {
        x = 10;
    } else {
        x = 20;
    }
    return x;
}

long clamp(long value, long high) {
    long result;
    if ((value > high)) {
        result = high;
    } else {
        result = value;
    }
    return result;
}

long branch_then_loop(long n) {
    long total;
    if ((n > 0)) {
        total = n;
    } else {
        total = 0;
    }
    while ((total > 0)) {
        total = (total - 1);
    }
    return total;
}
