# Reglas de decisión del Atlas / LEONES

Estas reglas quedan fijadas para evitar que futuras incorporaciones degraden la calidad metodológica del Atlas.

## Regla 1 — Apertura

La etiqueta comercial o declarativa de un proveedor no es suficiente para elevar la clasificación JGB.

`Open weights` en una fuente ≠ `JGB 3` automáticamente.

Debe existir evidencia de los derechos y condiciones exigidos por el marco.

## Regla 2 — Evidencia

Toda clasificación JGB debe conservar:

- fuente;
- URL cuando exista;
- fecha de verificación;
- evidencia concreta;
- confianza.

Cuando falte evidencia suficiente, se usa `unknown`.

## Regla 3 — Separación de dimensiones

Nunca mezclar en un único campo:

- apertura;
- calidad;
- rendimiento;
- self-hostability;
- coste.

## Regla 4 — Rendimiento

Una medición es siempre contextual:

`modelo + hardware + runtime + cuantización + workload + contexto`.

No convertir `tokens/s` de una configuración en una propiedad universal del modelo.

## Regla 5 — Viabilidad

La recomendación primero comprueba viabilidad técnica. Después optimiza preferencias.

Orden mínimo:

1. memoria;
2. compatibilidad runtime/hardware;
3. contexto y modalidad;
4. disponibilidad de ejecución;
5. rendimiento;
6. calidad;
7. preferencias.

## Regla 6 — Barahona y JGB

Son taxonomías independientes.

No se sustituye una por otra y no se transforma ninguna en un score universal de calidad.

## Regla 7 — Prospección

La prospección diaria debe detectar al menos:

- nuevos modelos;
- nuevas versiones;
- cambios de licencia/condiciones;
- nuevos pesos o formatos;
- nuevos runtimes;
- nuevas mediciones;
- cambios relevantes en hardware/compatibilidad.

Los cambios que afecten a JGB deben generar una revisión.

## Regla 8 — Recomendación explicable

Cada resultado del recomendador debe poder explicar:

- por qué es viable;
- qué evidencia de rendimiento existe;
- qué evidencia de calidad existe;
- qué clasificación JGB tiene y por qué;
- qué restricciones del usuario satisface;
- qué incertidumbres permanecen.

## Regla 9 — Conservadurismo

Es preferible `unknown` a una clasificación no demostrada.

Es preferible una recomendación con confianza media y evidencia explícita a un ranking aparentemente preciso pero no auditable.

## Regla 10 — Evolución

Las reglas son versionadas. Cualquier cambio metodológico debe documentarse y no sobrescribir silenciosamente una clasificación histórica.
