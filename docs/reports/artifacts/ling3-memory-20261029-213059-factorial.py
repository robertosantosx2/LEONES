def factorial(n):
    if n < 0:
        raise ValueError("El factorial no está definido para números negativos.")
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


# Prueba 1: factorial(0) debe devolver 1
print(factorial(0))

# Prueba 2: factorial(5) debe devolver 120
print(factorial(5))

# Prueba 3: factorial(10) debe devolver 3628800
print(factorial(10))
