# Contrato de scripts LEONES

> **RC1:** mínimo código necesario, máxima documentación útil y ninguna duplicación funcional.

Los scripts de LEONES deben poder ser entendidos y utilizados por una persona con conocimientos mínimos de programación. Un script no es una arquitectura: es una pieza pequeña que responde a una pregunta concreta dentro de un recorrido mayor.

## Reglas obligatorias

1. **Una responsabilidad:** cada script responde a una pregunta o realiza una tarea principal.
2. **Minimalismo:** usar la solución más sencilla que conserve el comportamiento necesario. No añadir abstracciones por anticipación.
3. **Legibilidad antes que brevedad:** evitar varias instrucciones en una línea, nombres crípticos y expresiones difíciles de leer.
4. **Comentarios útiles:** explicar el propósito y, sobre todo, el motivo de las decisiones que no sean obvias. No comentar código evidente.
5. **Docstring de entrada:** todo script ejecutable debe indicar qué hace, qué recibe, qué produce y sus límites principales.
6. **Interfaz explícita:** los argumentos de línea de comandos deben tener nombres claros y una descripción comprensible.
7. **Errores accionables:** cuando algo falla, indicar qué se esperaba y qué puede hacer la persona para corregirlo.
8. **Sin trabajo oculto:** un script no debe instalar paquetes, publicar datos, modificar repositorios ni ejecutar cargas físicas salvo que su propósito lo indique expresamente.
9. **Reutilización prudente:** no duplicar una función ya existente. Si compartir código realmente simplifica el proyecto, usar un módulo pequeño y bien documentado.
10. **Prueba:** todo cambio funcional debe conservar o ampliar las pruebas existentes.
11. **README operativo:** todo script del núcleo debe estar descrito en `scripts/README.md` y, cuando necesite instrucciones propias, tener documentación específica junto al componente.
12. **Fronteras explícitas:** selección, ejecución, medición, evidencia y publicación deben permanecer separadas salvo que exista un contrato que justifique unirlas.
13. **Procedencia:** ningún script puede transformar por conveniencia `estimated`, `reported`, `observed`, `measured`, `verified` o `unknown` en otra categoría.

## Criterio de aceptación

Un script se considera limpio cuando una persona que no conoce el proyecto puede responder, leyendo sus primeros comentarios y la interfaz, a estas cuatro preguntas:

- ¿Para qué sirve?
- ¿Qué necesito antes de ejecutarlo?
- ¿Qué va a cambiar o producir?
- ¿Qué no hace?

Para un script del núcleo RC1 también debe ser posible contestar:

- ¿Qué contrato consume?
- ¿Qué contrato entrega?
- ¿Dónde encaja en el camino mínimo?
- ¿Qué parte requiere ejecución física real?

La complejidad accidental debe eliminarse. La complejidad propia del problema puede permanecer, pero debe quedar explicada.

## Documentación interna

Los comentarios no deben describir obviedades como "incrementamos el contador". Deben preservar decisiones que una futura simplificación podría romper accidentalmente, por ejemplo:

- por qué se rechaza una entrada;
- por qué un valor desconocido permanece ausente;
- por qué un límite de generación es obligatorio;
- por qué una función delega en otro módulo en lugar de duplicar su lógica;
- por qué una medición no puede ser promocionada automáticamente a `verified`.

## Documentación externa

`README.md` y la documentación de fase explican el **modelo mental** de la herramienta: cuándo usarla, cuándo no usarla, qué entrada necesita, qué salida entrega y qué viene después.

No se debe copiar el código al README. Se debe documentar el contrato.

## Política de migración

Esta norma se aplica a los scripts nuevos y a todo script que se modifique. Los scripts antiguos se simplificarán de forma incremental, sin reescrituras masivas que puedan cambiar su comportamiento sin necesidad.

Antes de mover un script a `deprecated` se deben identificar sus consumidores. Si existe un consumidor activo, primero se migra o se declara explícitamente por qué permanece fuera del núcleo RC1.

Un movimiento a `deprecated` debe conservar trazabilidad y explicar qué pieza lo sustituye, si existe.

## Regla RC1

> **Si una pieza puede eliminarse sin romper el camino mínimo ni perder conocimiento, no debe mantenerse en el núcleo por inercia histórica.**
