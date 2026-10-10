def choose(flag)
  if (flag > 0)
    x = 10
  else
    x = 20
  end
  return x
end

def clamp(value, high)
  if (value > high)
    result = high
  else
    result = value
  end
  return result
end

def branch_then_loop(n)
  if (n > 0)
    total = n
  else
    total = 0
  end
  while (total > 0)
    total = (total - 1)
  end
  return total
end
