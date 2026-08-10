# Estimación inicial de tiempos por tarea LOAS

Estas cifras son **estimaciones operativas**, no mediciones oficiales. Sirven para que LOAS pueda comparar UX antes de disponer de suficientes resultados metaLOAS reales.

La referencia principal deja de ser tok/s y pasa a ser **tiempo de tarea completada**. El rendimiento de inferencia sigue siendo una variable explicativa.

## Escala propuesta

| Tiempo de tarea | UX LOAS | Interpretación |
|---|---|---|
| < 5 s | Excelente | Respuesta prácticamente inmediata |
| 5–10 s | Muy buena | Fluida para interacción frecuente |
| 10–30 s | Buena | Usable para tareas normales |
| 30–60 s | Aceptable | Usable, pero con espera perceptible |
| 1–3 min | Lenta | Solo razonable para tareas de mayor complejidad |
| > 3 min | No mínimamente usable | Requiere optimización o ejecución asíncrona |

## LOTB — primera estimación

| Tarea | Objetivo | Estimación inicial |
|---|---|---:|
| B01 Memoria/localidad | Mantener contexto y continuar una tarea | 5–15 s |
| B02 Archivos | Leer, modificar y devolver un archivo | 10–30 s |
| B03 Multietapa | Completar una secuencia de acciones | 20–60 s |
| B04 Recuperación ante fallo | Detectar fallo, corregir y continuar | 30–120 s |
| B05 Coding local | Analizar, editar y comprobar código | 30–180 s |

Estas ventanas **no son límites de aprobación**. El resultado definitivo debe obtenerse mediante mediciones reproducibles de metaLOAS.

## Regla fundamental

Una pila puede superar 10 tok/s y seguir ofreciendo una mala UX si genera demasiados pasos, llamadas de herramientas, esperas o errores. Por ello LOAS debe registrar al menos:

- tiempo total de tarea;
- tok/s;
- número de pasos agentivos;
- llamadas a herramientas;
- errores/reintentos;
- resultado final: PASS/FAIL;
- modelo, cuantización, backend y harness;
- perfil de hardware.

## Prioridad

Cuando existan mediciones suficientes, la web debe mostrar **tiempos observados** por encima de estas estimaciones. Las estimaciones deben quedar etiquetadas como tales.
