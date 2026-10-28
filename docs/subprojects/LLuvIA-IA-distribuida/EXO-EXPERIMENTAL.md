# EXO en LLuvIA — evaluación experimental

**Estado:** EXPERIMENTAL · evaluación documental  
**Fecha de revisión:** 2026-10-28  
**Repositorio upstream:** https://github.com/exo-explore/exo  
**Licencia upstream:** Apache-2.0 (verificar la licencia del checkout/versionado antes de redistribuir componentes).

## 1. Decisión provisional

EXO se incorpora al radar experimental de LLuvIA como **posible motor de inferencia distribuida entre dispositivos**, no como sustituto del gateway, del router ni de los servicios especialistas. Esta ficha registra una hipótesis de integración y un plan de validación; **no significa que EXO esté instalado, ejecutado, medido o validado en LEONES**.

## 2. Encaje arquitectónico

LLuvIA distribuye servicios especializados por función (por ejemplo, código, idiomas, matemáticas, OCR, audio/TTS y vídeo). EXO apunta a otro problema complementario: coordinar varios dispositivos para ejecutar una inferencia/modelo y distribuir su carga cuando el modelo o la memoria lo justifiquen.

Arquitectura propuesta:

```text
Cliente
  |
LLuvIA Gateway / políticas / router
  |---------------------------|
Servicios especialistas     Adaptador EXO (experimental)
(código, OCR, audio, etc.)          |
                            Cluster EXO de nodos compatibles
                                     |
                              métricas y observabilidad
```

La selección entre servicio especialista y EXO debe ser explícita y basada en capacidades verificadas, no en la mera disponibilidad del clúster. Mantener una API estable detrás de un adaptador reduce el acoplamiento con la implementación interna de EXO.

## 3. Capacidades a evaluar

La documentación upstream describe descubrimiento de dispositivos, coordinación de clúster, paralelismo/particionado de modelos y APIs compatibles con interfaces habituales de inferencia. La cobertura concreta depende de la versión, del modelo, del sistema operativo y del backend.

Fuentes primarias:
- Proyecto y documentación: https://github.com/exo-explore/exo
- Plataformas y compatibilidad: https://github.com/exo-explore/exo/blob/main/PLATFORMS.md
- Benchmarks del proyecto: https://github.com/exo-explore/exo/tree/main/bench

Los nombres de APIs, modelos y plataformas compatibles deben volver a verificarse contra la versión que se pruebe; no se consideran un contrato permanente de LLuvIA.

## 4. Riesgo principal: Linux y aceleración

La revisión documental de 2026-10-28 indica que la ruta Linux no debe darse por equivalente a las rutas aceleradas más maduras de otras plataformas: el soporte GPU en Linux aparece como limitado/en desarrollo en la documentación consultada, y la ejecución CPU no implica aceleración CUDA.

**No asumir que EXO aprovechará la NVIDIA RTX 3050 Laptop de 4 GB VRAM del equipo de desarrollo ni las GPU NVIDIA de otros nodos.** Antes de planificar recursos, verificar en la versión concreta: backend disponible, detección de dispositivos, uso real de GPU, memoria asignada y compatibilidad de cada modelo. No se ha confirmado compatibilidad específica de LFM/LFM3.

## 5. Viabilidad preliminar

| Caso | Evaluación inicial | Condición |
|---|---|---|
| Repartir un modelo de texto entre dos nodos Ubuntu CPU | Candidato a prueba | Modelo/backend admitido y red estable |
| Modelo pequeño que cabe cómodamente en un nodo | Prioridad baja para EXO | Comparar contra inferencia local sencilla |
| Modelo mayor que la memoria disponible de un nodo | Caso de interés | Verificar particionado, RAM total y sobrecoste de comunicación |
| Aceleración de RTX 3050 bajo Linux | No confirmada | Prueba técnica explícita; no inferir soporte |
| Pipeline de servicios distintos (OCR, TTS, audio, vídeo) | No es el papel principal de EXO | Mantener servicios especialistas LLuvIA |
| LFM/LFM3 distribuido | Desconocido | Confirmar arquitectura y soporte en upstream |

Esta tabla es una **estimación cualitativa**, no un benchmark. No asignar tokens/s, latencias ni límites de memoria sin mediciones reproducibles.

## 6. Protocolo de validación propuesto

### Fase A — verificación estática
1. Fijar una versión/tag/commit concreto de EXO.
2. Registrar licencia, requisitos, plataformas, backends y modelos declarados compatibles.
3. Comprobar el método de instalación en Ubuntu y sus dependencias sin alterar los servicios actuales de inferencia.
4. Identificar interfaces de API, límites y opciones de apagado/recuperación.

### Fase B — dos nodos CPU
1. Usar dos nodos Ubuntu de 16 GB RAM, inicialmente sin GPU.
2. Seleccionar un modelo pequeño expresamente admitido por esa versión.
3. Medir primero el modelo en un solo nodo y luego en dos nodos.
4. Repetir con un modelo cuyo consumo justifique explorar el particionado distribuido, si hay uno compatible.
5. Registrar configuración, commit, cuantización, contexto, tokens de entrada/salida, número de repeticiones y condiciones de carga.

### Fase C — evaluación y fallos
Medir al menos:
- tiempo de carga y TTFT;
- tokens/s de prefill y generación, cuando la herramienta lo permita;
- RAM máxima por nodo y memoria del modelo;
- tráfico de red y latencia entre nodos;
- concurrencia, errores y comportamiento al perder un nodo;
- calidad funcional básica y compatibilidad de la API.

Comparar contra el baseline de un nodo con el mismo modelo y parámetros. Separar claramente **ESTIMATED** de **MEASURED** y conservar logs/configuración.

### Fase D — integración controlada
Solo si la prueba aporta valor:
1. crear un adaptador EXO aislado detrás del gateway LLuvIA;
2. añadir comprobación de salud, timeout, límites de concurrencia y fallback a un servicio alternativo;
3. hacer pruebas de contrato y E2E sin cambiar la ruta por defecto;
4. escalar de dos nodos a más nodos solo tras analizar latencia, comunicación y recuperación.

## 7. Criterios de aceptación

EXO no debe pasar a integración recomendada hasta que:
- exista una ejecución reproducible sobre la plataforma objetivo;
- el soporte real de modelo/backend esté documentado;
- la comparación de uno frente a varios nodos muestre una ventaja o una capacidad que compense el coste;
- se documenten memoria, latencia, tokens/s, tráfico y comportamiento ante fallos;
- el adaptador pueda desactivarse sin afectar al router ni a los servicios LLuvIA existentes.

## 8. Conclusión

**Decisión: mantener EXO en EXPERIMENTAL / pendiente de validación física.** Su posible valor es distribuir una inferencia entre dispositivos; LLuvIA conserva el control de políticas y enrutamiento y sigue usando servicios especialistas para tareas distintas. La compatibilidad con GPU NVIDIA en Linux y con LFM/LFM3 queda expresamente sin confirmar. No se han realizado instalaciones ni pruebas físicas como parte de esta evaluación.

## Historial

- 2026-10-28 — primera ficha documental; evaluación preliminar y protocolo de validación. Sin instalación ni mediciones.
