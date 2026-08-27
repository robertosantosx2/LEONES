# JALÓN 1 — CI, #62 y puente de ejecución

**Estado: 🟢 CERRADO**  
**Fecha de cierre: 2026-08-27**

## Objetivo

Dejar integrada y protegida la primera cadena V1.1 de selección de runtime, autorización de ejecución y puente hacia benchmark/evidencia, con CI y contratos como barrera de aceptación.

## Criterios de cierre

- [x] Pull request **#62** integrado en `main`.
- [x] Registry/selección de runtimes y adapters V1.1 integrados.
- [x] Puente runtime → benchmark/evidence integrado.
- [x] La autorización de ejecución física exige un comando de runtime confiable.
- [x] La cadena A01 de referencia queda documentada como ejecución real de extremo a extremo.
- [x] Los cambios posteriores inmediatos permanecen dentro de la misma cadena de endurecimiento; el último commit registrado corrige el parseo del throughput de generación de llama.cpp.

## Evidencia de repositorio

El merge de **#62** está en `main` como commit `b79a51b8f85be3e4f0fc134d1f822ee27ef06064`, con mensaje `Merge V1.1 runtime registry, adapters and benchmark/evidence bridge`.

El commit inmediatamente posterior `e5c5e13c107fcad711488215b06c7add8ad8ab83` endurece la autorización exigiendo un comando de runtime confiable. El estado más reciente registrado es `44ef5e9ae75f47eb4428418d9a5af09d1b457f77`, que corrige el parseo del throughput de generación de llama.cpp.

## Límite del cierre

Este jalón **no certifica todavía una nueva medición física en Debian**. Certifica que la arquitectura, los contratos y el puente necesarios para hacerla están integrados en `main`.

La ejecución física, su medición y la conservación de evidencia real pertenecen al **JALÓN 2**.

## Decisión

**JALÓN 1 queda cerrado.** No se reabre salvo que un cambio posterior rompa sus contratos o invariantes.
