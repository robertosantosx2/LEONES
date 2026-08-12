# LEONES — reglas de desarrollo

Estas reglas son deliberadamente simples.

## 1. Un script, una responsabilidad

Cada script debe hacer una cosa principal. Evitamos módulos que descarguen,
instalen, configuren, ejecuten y evalúen todo a la vez.

## 2. Preferir composición a magia

Los componentes se conectan mediante interfaces pequeñas y datos explícitos.
Un componente no debe conocer detalles internos de otro si puede evitarlos.

## 3. Documentar antes de complicar

Todo script nuevo debe explicar al principio:

- qué hace;
- qué no hace;
- qué entradas necesita;
- qué salida produce;
- qué dependencias externas utiliza.

## 4. Dependencias mínimas

La librería estándar de Python es la primera opción. Una dependencia externa
solo se añade cuando aporta una capacidad que no conviene mantener en LEONES.

## 5. Fallar de forma explícita

No ocultar errores ni inventar fallbacks silenciosos. Si falta un runtime,
un modelo, una herramienta o una capacidad de hardware, debe quedar claro.

## 6. Datos y lógica separados

Atlas contiene datos. Router decide. Runtime ejecuta. Benchmark mide. No
mezclamos esas responsabilidades para ahorrar unas líneas de código.

## 7. Reproducibilidad

Las operaciones que produzcan resultados deben poder repetirse con entradas
identificables y configuración explícita.

## 8. No sobreingeniería

LEONES debe crecer por incrementos pequeños y comprobables. Una abstracción
solo se añade cuando existe una necesidad real.
