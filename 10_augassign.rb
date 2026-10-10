def add_assign(x, y)
  x = (x + y)
  return x
end

def sub_assign(x, y)
  x = (x - y)
  return x
end

def mul_assign(x, y)
  x = (x * y)
  return x
end

def chain_assign(a, b, c)
  a = (a + b)
  a = (a * c)
  return a
end
