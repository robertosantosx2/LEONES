# Router + Hardware Intelligence

## Principio de transparencia

LEONES no debe afirmar que un modelo cabe en un equipo si Atlas todavía no contiene el dato que permite demostrarlo.

Por eso esta primera pieza establece el límite de integración, pero **no inventa requisitos de RAM** para los modelos existentes.

```text
Hardware Intelligence
        ↓
 HardwareLimits
        ↓
 Router hardware filter
        ↓
 candidatos realmente evaluables
```

## Estado actual

`HardwareLimits` registra la RAM disponible. `filter_by_hardware` recibe candidatos, pero como los candidatos actuales todavía no declaran un requisito mínimo de RAM, no elimina ninguno.

Esto es deliberado.

## Próximo paso

Añadir a Atlas evidencia de requisitos de ejecución por modelo y cuantización. Entonces el filtro podrá hacer una comprobación real:

```text
RAM disponible >= RAM requerida
```

Más adelante se añadirán VRAM, contexto, backend, cuantización y otros límites, cada uno con evidencia propia.
