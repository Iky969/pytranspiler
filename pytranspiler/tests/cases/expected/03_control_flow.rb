def max_of(a, b)
  if (a > b)
    return a
  else
    return b
  end
end

def sign(x)
  if (x > 0)
    return 1
  elsif (x < 0)
    return (-1)
  else
    return 0
  end
end

def sum_to(n)
  total = 0
  i = n
  while (i > 0)
    total = (total + i)
    i = (i - 1)
  end
  return total
end
