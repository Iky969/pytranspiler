#include <stdbool.h>

long square(long x) {
    return (x * x);
}

long add(long a, long b) {
    return (a + b);
}

long sum_of_squares(long a, long b) {
    return add(square(a), square(b));
}

long factorial(long n) {
    if ((n <= 1)) {
        return 1;
    } else {
        return (n * factorial((n - 1)));
    }
}
