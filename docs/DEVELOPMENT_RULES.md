# LEONES — reglas de desarrollo

Estas reglas son deliberadamente simples.

> **Regla principal: scripts sencillos que hagan las menores cosas posibles y estén muy documentados.**

## 1. Un script, una responsabilidad

Cada script debe hacer una cosa principal. Evitamos módulos que descarguen,
instalen, configuren, ejecuten y evalúen todo a la vez.

Ejemplos:

- `hardware`: detectar hardware.
- `model`: describir o localizar un modelo.
- `infer`: ejecutar inferencia.
- `lotb`: ejecutar una prueba LOTB.
- `report`: convertir resultados en informes.
- `publish`: publicar resultados preparados.
- `stats`: agregar resultados para la web.

## 2. Preferir composición a magia

Los componentes se conectan mediante interfaces pequeñas y datos explícitos.
Un componente no debe conocer detalles internos de otro si puede evitarlos.

## 3. Documentar antes de complicar

Todo script nuevo debe explicar al principio:

1. qué hace;
2. qué no hace;
3. qué entradas necesita;
4. qué salida produce;
5. qué dependencias externas utiliza;
6. un ejemplo mínimo de uso;
7. sus limitaciones conocidas.

El código debe poder entenderse sin reconstruir una arquitectura oculta.

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

## 9. Documentación web sincronizada

Cada avance relevante de arquitectura, operación o metodología debe reflejarse
también en la web pública. La documentación no debe quedar retrasada respecto
al código.

## 10. Autonomía sin acoplamiento

LEONES no debe depender de una aplicación de escritorio concreta. Los runtimes
externos son adaptadores intercambiables.
