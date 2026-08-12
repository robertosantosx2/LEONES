# Router ↔ Leones Atlas

## Objetivo

Conectar el Router con el catálogo real de modelos sin mezclar responsabilidades.

```text
Leones Atlas → Router candidates → Leones Router → Decision
```

`router_atlas` solo lee los modelos registrados y los transforma en candidatos. La decisión continúa siendo responsabilidad de `router_simple`.

## Ejemplo

```python
from leones.router_atlas import candidates_from_atlas
from leones.router_simple import route

candidates = candidates_from_atlas("leones_atlas.sqlite")
decision = route("write Python code", candidates)
print(decision)
```

## Importante

Todavía no se selecciona automáticamente por RAM, tamaño, benchmark o velocidad. Esos criterios llegarán después y deberán quedar explícitos en Atlas y Router.
