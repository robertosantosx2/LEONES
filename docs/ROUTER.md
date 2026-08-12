# Leones Router

## Objetivo

`router_simple` convierte una petición en una primera decisión explícita de modelo y backend.

## Primera versión

El Router no pretende resolver todavía toda la optimización de inferencia. Utiliza una regla pequeña y auditable:

1. identifica una capacidad aproximada de la tarea;
2. recorre los candidatos en el orden proporcionado;
3. selecciona el primer candidato que declara esa capacidad;
4. conserva el backend declarado por el candidato.

Capacidades iniciales:

- `coding`
- `reasoning`
- `general`

## Ejemplo

```python
from leones.router_simple import Candidate, route

candidates = [
    Candidate("qwen-general", ("general",)),
    Candidate("qwen-coder", ("coding",)),
]

print(route("write Python code", candidates))
```

## Qué no hace

- no descarga modelos;
- no modifica Atlas;
- no ejecuta inferencia;
- no inventa benchmarks;
- no usa una puntuación opaca.

## Evolución prevista

Posteriormente el Router podrá incorporar hardware, memoria disponible, cuantización, contexto, latencia objetivo, benchmark y coste. Cada criterio deberá ser documentado y comprobable.
