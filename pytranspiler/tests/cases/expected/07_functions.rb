def square(x)
  return (x * x)
end

def add(a, b)
  return (a + b)
end

def sum_of_squares(a, b)
  return add(square(a), square(b))
end

def factorial(n)
  if (n <= 1)
    return 1
  else
    return (n * factorial((n - 1)))
  end
end
