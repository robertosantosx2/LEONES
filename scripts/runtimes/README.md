# Runtime adapters — RC1

Los adapters de runtime son **conectores**, no runtimes propios de LEONES.

## Regla

Un adapter debe hacer lo mínimo necesario para traducir un plan autorizado al
runtime externo correspondiente. No debe duplicar selección, benchmark,
evaluación ni publicación.

```text
LEONES decide
     ↓
plan autorizado
     ↓
adapter mínimo
     ↓
runtime externo
     ↓
resultado observado
     ↓
evidencia LEONES
```

## Estado RC1

- `llama_cpp_adapter.py` — **activo y probado como fallback de medición**.
- `run_llama_cpp_selected.py` — **activo** como puente de ejecución física.
- adapters declarativos de otros runtimes — **compatibilidad/registro**, no implican que LEONES los ejecute localmente.
- ODS y Magnitude — se integrarán desde sus propias capacidades; no se recrearán dentro de LEONES.

## Regla de evolución

Antes de implementar un adapter nuevo hay que demostrar que el runtime externo
es necesario para un escenario RC1 y que no existe ya una pieza equivalente.

AirLLM y FreeToken se estudiarán como aportaciones a ODS/Magnitude o como
conectores cuando llegue su fase correspondiente. No se incorporan ahora como
una segunda arquitectura de inferencia de LEONES.

## Medición

El adapter nunca convierte una estimación en medición. La medición y la
aceptación de evidencia pertenecen al contrato de benchmark de LEONES.

## Desarrollo

Los cambios de adapters deben conservar:

1. autorización previa del plan;
2. argumentos separados, nunca shell construido como texto;
3. límites explícitos para ejecuciones reproducibles;
4. errores accionables;
5. pruebas de contrato;
6. documentación del runtime externo que realmente se presupone.
