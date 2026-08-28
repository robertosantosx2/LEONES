# LEONES Rules — STRICT RC1

> **Norma complementaria obligatoria de `docs/LEONES-Rules.md`.**
>
> Esta regla queda congelada para Release Candidate 1.

## Regla STRICT — código mínimo y documentación máxima

> **Poco código, cada pieza con una responsabilidad, comentarios que expliquen decisiones y README que explique cómo utilizarla.**

Esta frase no es una preferencia de estilo. Es un **criterio de aceptación** para cualquier pieza que entre o permanezca en el camino operativo RC1.

### 1. Poco código

Implementar solamente lo necesario para la responsabilidad declarada.

Antes de añadir código hay que demostrar que no existe ya una pieza reutilizable, una capacidad del upstream o una integración más simple.

### 2. Una responsabilidad por pieza

Cada script, módulo o adapter debe tener una responsabilidad principal identificable por su nombre y documentación.

Si una pieza decide, ejecuta, mide, valida y publica a la vez, debe dividirse o justificarse explícitamente.

### 3. Comentarios que expliquen decisiones

Los comentarios internos deben explicar **por qué** existe una decisión no obvia, qué contrato protege o qué limitación externa obliga a una implementación concreta.

No se deben llenar los scripts de comentarios que simplemente repitan el código.

### 4. README que explique cómo utilizarla

Toda pieza reutilizable debe disponer de documentación externa que explique como mínimo:

- para qué sirve;
- cuándo utilizarla;
- cuándo no utilizarla;
- entradas;
- salidas;
- ejemplo mínimo;
- dependencias;
- relación con el siguiente paso del pipeline;
- contrato o evidencia relacionada.

### 5. Gate de aceptación

Una pieza no se considera `RC1 accepted` hasta cumplir:

```text
poco código
    +
responsabilidad única
    +
comentarios de decisiones
    +
README operativo
    +
tests apropiados
    +
sin duplicación funcional
    =
aceptada
```

Una excepción requiere quedar documentada y registrada en Git.

## Relación con las demás Rules

Esta norma refuerza especialmente:

- `LEONES Rules` — pequeño por diseño;
- `upstream-first`;
- no duplicar ODS/Magnitude/Hermes;
- deprecación limpia;
- documentación antes de complicar;
- Ubuntu solo cuando sea imprescindible.

La referencia normativa completa continúa siendo `docs/LEONES-Rules.md`; este documento hace **explícito y estricto** el criterio de implementación para RC1.
