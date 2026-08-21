# Política canónica para clones y subproyectos externos

**Estado: FIJADA**  
**Ámbito: todo subproyecto, upstream, fork, vendor o clon incorporado a LEONES**

## Regla principal

LEONES nunca debe convertir el clon de un proyecto externo en un fork opaco y difícil de actualizar.

Todo proyecto externo incorporado seguirá esta separación:

```text
UPSTREAM EXTERNO (inmutable / SHA fijado)
                |
                v
       AUDITORÍA + PROVENIENCIA
                |
                v
     CAPA DE INTEGRACIÓN LEONES
                |
                +--> patches/cambios LEONES
                +--> adaptadores
                +--> contratos
                +--> tests
                +--> CI
                |
                v
       BENCHMARK / HARDWARE LOCAL
```

## 1. El upstream es una referencia reproducible

- Preferir submódulo Git cuando el proyecto tenga repositorio Git.
- Fijar siempre un commit SHA, nunca depender únicamente de `main`/`master`.
- Registrar repositorio, SHA, versión/tag si existe, licencia y fecha de incorporación.
- No modificar silenciosamente el contenido del submódulo upstream.
- Una actualización de upstream debe ser un cambio explícito y revisable.

## 2. Las correcciones de LEONES están fuera del upstream

Toda modificación necesaria para LEONES debe vivir en la capa de integración, mediante uno de estos mecanismos:

1. adaptador o wrapper LEONES;
2. patch explícito versionado;
3. configuración/overlay;
4. fork únicamente cuando sea imprescindible y con relación de procedencia documentada.

Nunca se debe editar un fichero del clon upstream y después tratarlo como si fuera una modificación propia no diferenciada.

## 3. Auditoría obligatoria antes de integrar

Cada nuevo subproyecto debe tener, como mínimo:

- `UPSTREAM_AUDIT.md`;
- `UPSTREAM_SNAPSHOT.md` o equivalente;
- origen y SHA/versionado del upstream;
- licencia;
- inventario de dependencias;
- API pública utilizada por LEONES;
- defectos encontrados;
- riesgos de mantenimiento;
- estrategia de actualización;
- separación de dependencias CPU/GPU/servicios externos.

## 4. CI antes de usar el Debian del usuario

La validación reproducible se hace primero en GitHub Actions:

- instalación limpia;
- import tests;
- unit tests;
- contract tests;
- packaging/build;
- lint/type checks cuando proceda;
- tests de integración simulables;
- submodules correctamente fijados.

El Debian del usuario **no es el entorno de desarrollo principal de subproyectos externos**.

## 5. Debian = laboratorio de hardware

Una vez verde la validación de software, el equipo local se usa para aquello que CI no puede representar fielmente:

- CPU y número de hilos;
- instrucciones disponibles;
- RAM y presión de memoria;
- ancho de banda;
- latencia/rendimiento del disco;
- GPU y VRAM;
- CUDA/ROCm cuando exista;
- consumo;
- inferencia local;
- tokens/s;
- latencia real;
- comparación de modelos y cuantizaciones.

## 6. Dependencias

No se deben introducir paquetes por el procedimiento de "instalar hasta que deje de fallar".

Cada dependencia debe clasificarse como:

- core;
- opcional;
- proveedor remoto;
- GPU/CUDA;
- evaluación;
- demo/UI;
- desarrollo/test.

El baseline CPU debe mantenerse pequeño y reproducible.

## 7. Tests de contrato

Cuando el upstream exponga APIs que LEONES consume, se deben probar los contratos reales, no nombres inferidos por nombres de archivos o documentación antigua.

Los tests deben detectar expresamente:

- cambios de nombres de clases/funciones;
- cambios de tipos de retorno;
- cambios de shapes;
- cambios de configuración;
- dependencias obligatorias nuevas;
- servicios externos inesperadamente obligatorios.

## 8. Actualización de upstream

Una actualización seguirá siempre este ciclo:

```text
nuevo SHA
   |
   v
comparación con SHA anterior
   |
   v
auditoría de cambios
   |
   v
tests de contrato
   |
   v
CI
   |
   v
revisión PR
   |
   v
actualización aprobada
```

No se actualizará automáticamente un submódulo crítico sólo porque upstream haya cambiado.

## 9. Limpieza local

Cuando una tarea de desarrollo externo termine, la virtualenv y cachés temporales creados específicamente para ella pueden eliminarse del Debian del usuario.

No se deben ejecutar limpiezas globales destructivas (`apt autoremove`, purgas generales de Python, borrado indiscriminado de `/usr/local`, etc.) para resolver problemas de un único subproyecto.

## 10. Aplicación universal

Esta política se aplica desde ahora a **ODS, Magnitude, Buddy, Hermes, Atlas y cualquier futuro repositorio externo** incorporado a LEONES.

Es una regla de arquitectura y mantenimiento, no una recomendación opcional.
