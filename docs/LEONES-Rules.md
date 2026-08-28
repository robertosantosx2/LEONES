# LEONES Rules

> Normativa canónica de trabajo de LEONES.
>
> Para Release Candidate 1 se aplica junto con [`LEONES-Rules-STRICT.md`](LEONES-Rules-STRICT.md).

## 1. Propósito

LEONES debe ser pequeño por diseño y grande en evidencia, conocimiento y documentación.

Su responsabilidad propia es conectar conocimiento, hardware, selección, sistemas especializados, medición y publicación sin duplicar capacidades que ya existen en proyectos upstream.

## 2. Reutilizar antes de construir

Antes de escribir código nuevo hay que comprobar si la capacidad ya existe en:

- Atlas;
- LLMFit;
- ODS;
- Magnitude;
- Hermes cuando forme parte del sistema integrado;
- runtimes upstream;
- AirLLM;
- FreeToken;
- herramientas y estándares ya existentes.

La integración o upstream es preferible a mantener una implementación paralela.

## 3. Responsabilidad única

Cada componente debe tener una función clara. La selección decide; el runtime ejecuta; la medición mide; la evidencia conserva; Atlas conserva conocimiento; MANADA publica conocimiento colectivo.

## 4. Evidencia antes que afirmaciones

LEONES distingue como mínimo:

`estimated` → `reported` → `observed` → `measured` → `verified`.

Nunca se promociona una estimación como medición. Toda medición física debe conservar condiciones, procedencia y ejecución.

## 5. Investigación permanece

La reducción de RC1 es de producto operativo, no de conocimiento. Investigación, Atlas, prospección, apertura, benchmarks externos, hardware, precios/TCO y conocimiento histórico siguen formando parte de LEONES.

## 6. Upstream-first

Cuando una mejora de AirLLM o FreeToken sea útil para ODS o Magnitude:

1. demostrar utilidad;
2. identificar el punto correcto del upstream;
3. intentar aportarla upstream;
4. crear un conector mínimo solamente si upstream no es viable;
5. evitar forks permanentes sin justificación.

## 7. ODS y Magnitude no se duplican

La decisión posterior a LLMFit es entre el ecosistema ODS para escenarios SOHO y Magnitude para el asistente personal, cuando sean adecuados.

LEONES no reemplaza su agente, Hermes, motor de inferencia, herramientas o capacidades propias. LEONES aporta decisión, integración, medición y evidencia.

## 8. Hardware de consumo primero

Los tiers de hardware son una clasificación operativa para reducir el espacio de búsqueda. No son un benchmark y no sustituyen mediciones reales.

## 9. Documentación máxima

Una pieza operativa debe explicar qué hace, por qué existe, cómo se utiliza, entradas, salidas, dependencias, límites y relación con el pipeline.

## 10. Ubuntu como último gate

Ubuntu se utiliza para lo que solamente puede comprobarse físicamente: hardware efectivo, compatibilidad, instalación real, carga de modelos, rendimiento, comportamiento agentivo y consumo.

No se diseña arquitectura durante una prueba física.

## 11. Deprecación limpia

Cuando una pieza deje de pertenecer al camino canónico, se conserva su historial y se mueve a la zona deprecada con una nota que explique por qué dejó de ser canónica. No se borra conocimiento útil sin motivo.

## 12. Regla de decisión

Ante cualquier nueva propuesta, preguntar en este orden:

```text
¿ya existe?
  ↓ sí → ¿podemos reutilizarlo?
  ↓ sí → integrar
  ↓ no → ¿podemos contribuir upstream?
  ↓ sí → upstream
  ↓ no → pieza mínima propia
```

## 13. Criterio de cierre RC1

RC1 no se cierra por número de scripts. Se cierra cuando una ruta completa y reproducible demuestra:

```text
hardware
→ fit inicial
→ decisión LEONES
→ ODS/Magnitude
→ runtime real
→ tarea real
→ benchmark
→ evidencia
→ recomendación
→ MANADA
```

Las ampliaciones posteriores deben demostrar valor antes de entrar en el camino canónico.
