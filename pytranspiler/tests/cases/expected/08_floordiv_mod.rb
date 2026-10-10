def floor_div_pos(a, b)
  return (a / b)
end

def mod_pos(a, b)
  return (a % b)
end

def floor_div_neg(a, b)
  return ((0 - a) / b)
end

def mod_neg(a, b)
  return ((0 - a) % b)
end

def combined(a, b)
  q = (a / b)
  r = (a % b)
  return ((q * b) + r)
end
