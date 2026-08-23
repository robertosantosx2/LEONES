# LEONES — MSA `sc-local`

**Fuente:** https://msa.millaguie.net/#sc-local  
**Estado:** fuente incorporada · revisión de accesibilidad pendiente  
**Fecha de revisión:** 2026-08-23

## 1. Qué es esta ficha

Esta ficha registra `MSA / sc-local` como fuente de conocimiento de LEONES y documenta exactamente qué se ha podido verificar y qué no. No se inventa contenido cuando la fuente primaria no está accesible.

La URL proporcionada contiene el ancla `#sc-local`, por lo que la referencia apunta específicamente a una sección identificada como `sc-local` dentro de `msa.millaguie.net`.

## 2. Resultado de la revisión

Durante esta revisión se intentó acceder directamente a:

`https://msa.millaguie.net/#sc-local`

El acceso desde el entorno de revisión no pudo recuperar el sitio. La consulta web devolvió un error de acceso y las búsquedas públicas no produjeron una copia indexada utilizable de la sección `sc-local`.

Por tanto, **no es correcto afirmar todavía qué proyectos, cifras, arquitectura, benchmarks o recomendaciones contiene `sc-local`**. La ficha queda deliberadamente marcada como `UNRESOLVED` en cuanto a contenido primario.

## 3. Qué sí queda establecido

- La fuente solicitada por el proyecto es `msa.millaguie.net`.
- El objetivo de incorporación es la sección `sc-local`.
- La fuente debe considerarse una entrada de **descubrimiento / conocimiento externo**, no una medición de LEONES.
- Cualquier runtime, modelo, hardware, benchmark o relación que aparezca allí deberá conservar su procedencia original.
- Los datos externos deberán clasificarse como `reported` hasta que LEONES pueda verificarlos o reproducirlos.

## 4. Papel potencial en LEONES

Si `sc-local` contiene un catálogo o estudio de ejecución local, su papel natural dentro de LEONES será el de **fuente de prospección y descubrimiento**:

```text
MSA / sc-local
      ↓
descubrimiento
      ↓
identidad primaria
      ↓
quality gate
      ↓
candidate
      ↓
runtime-selection.v1
      ↓
benchmark LEONES
      ↓
evidence
```

No debe convertirse directamente en recomendación. La aparición de un proyecto en MSA no demuestra que sea el mejor runtime, ni que sus cifras sean reproducibles en el hardware de LEONES.

## 5. Qué se debe extraer cuando la fuente primaria vuelva a estar disponible

La revisión completa deberá capturar, por cada entrada relevante:

1. nombre exacto del proyecto;
2. URL primaria;
3. tipo de componente: runtime, server, stack, aplicación, harness, benchmark o herramienta;
4. arquitecturas/modelos soportados;
5. formatos y cuantizaciones;
6. backends y aceleradores;
7. requisitos de hardware;
8. estrategia de memoria/offload;
9. APIs e interfaces;
10. estado de mantenimiento/licencia;
11. benchmarks o cifras publicadas;
12. hardware y configuración de esas cifras;
13. relación con otras fuentes ya incorporadas;
14. posible papel en `runtime-selection.v1`;
15. necesidad de benchmark LEONES.

## 6. Regla de evidencia

`MSA / sc-local` será una **fuente externa**. No se copiarán cifras a los resultados medidos de LEONES. La procedencia deberá distinguir como mínimo:

- `reported` — publicado por la fuente;
- `observed` — observado por LEONES pero no reproducido completamente;
- `verified` — comprobado contra la fuente primaria;
- `measured` — ejecutado por el benchmark de LEONES.

## 7. Estado actual

**Clasificación:** `UNRESOLVED` — contenido primario no recuperable desde el entorno de revisión actual.

**Acción pendiente:** repetir la revisión cuando `msa.millaguie.net` sea accesible o cuando se disponga de una copia/exportación de `sc-local`.

**Importante:** esta clasificación no significa que la fuente carezca de valor. Significa únicamente que LEONES no debe rellenar sus contenidos por inferencia.
