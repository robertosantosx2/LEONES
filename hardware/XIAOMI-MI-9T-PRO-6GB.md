# Xiaomi Mi 9T Pro — plataforma móvil de referencia

**Estado:** plataforma de referencia declarada; caracterización física pendiente.  
**Campaña:** [plan de pruebas](../docs/subprojects/Mobile-LLMs-ARM/devices/XIAOMI-MI-9T-PRO-TEST-PLAN.md) · [matriz de runtimes](../docs/subprojects/Mobile-LLMs-ARM/devices/XIAOMI-MI-9T-PRO-RUNTIME-MATRIX.md) · [protocolo de benchmark](../docs/subprojects/Mobile-LLMs-ARM/devices/XIAOMI-MI-9T-PRO-BENCHMARK-PROTOCOL.md)

## Identidad y datos comunicados

| Campo | Valor | Procedencia / estado |
|---|---|---|
| Dispositivo | Xiaomi Mi 9T Pro | Declarado por el usuario |
| RAM nominal | 6 GB | Declarado por el usuario |
| CPU | Octa-core, hasta 2,84 GHz | Declarado por el usuario; pendiente de lectura del dispositivo |
| SoC esperado | Qualcomm Snapdragon 855 | Identificación del modelo comercial; confirmar con Android |
| GPU esperada | Qualcomm Adreno 640 | Identificación del SoC; confirmar driver y capacidades |
| DSP/AI | Qualcomm Hexagon 690 | Identificación de plataforma; no implica soporte LLM |
| Almacenamiento libre | Más de 30 GB | Declarado por el usuario; fecha y método de medida pendientes |
| Android/API | Desconocido | Inventario pendiente |
| Root | Desconocido | Inventario pendiente |
| ABI / kernel / firmware | Desconocidos | Inventario pendiente |
| Estado térmico/batería | Desconocido | Inventario pendiente |

Los elementos marcados como esperados son hipótesis de identificación de la variante comercial, no una lectura de hardware obtenida del terminal. No publicar capacidades de aceleración como verificadas hasta capturar la salida del dispositivo.

## Propósito en LEONES

Plataforma ARM64 de referencia para Mobile-LLMs-ARM, complementaria a la estación Ubuntu MSI. La campaña caracterizará inferencia local de modelos compactos y comparará CPU, GPU y, si la plataforma de software lo permite, DSP/HTP.

La primera ruta será **Android sin root**, sin desbloquear bootloader, cambiar ROM, instalar firmware ni modificar particiones. Root se registrará como capacidad opcional y solo se utilizará en experimentos posteriores que lo requieran y cuenten con autorización explícita.

## Perfil esperado del SoC (pendiente de confirmar)

- Snapdragon 855 / familia SM8150.
- CPU Kryo 485: configuración heterogénea de núcleos basada en Cortex-A76/A55; no tratar los ocho núcleos como equivalentes.
- GPU Adreno 640.
- DSP Hexagon 690 / plataforma Qualcomm AI de esa generación.

La presencia de Hexagon no demuestra que QNN, HTP, FastRPC o un runtime moderno puedan ejecutar modelos LLM en este dispositivo. Cada combinación requiere una prueba de compatibilidad y ejecución efectiva.

## Inventario físico pendiente

Recopilar mediante ADB y/o Termux sin root:

- fabricante, modelo, producto, SoC y board;
- Android release, API level, build fingerprint y kernel;
- ABI primaria/secundarias y características CPU visibles;
- memoria total/disponible y almacenamiento libre;
- versión Vulkan, extensiones y driver GPU si están expuestos;
- estado de batería, temperatura y thermal status cuando Android lo permita;
- restricciones de batería, procesos y ahorro energético.

Comandos iniciales y campos esperados están en el plan de pruebas. No recopilar IMEI, número de serie, MAC, cuentas ni otros identificadores personales. Redactar identificadores únicos de las salidas antes de archivarlas.

## Límites y evidencia

- **Declarado:** datos facilitados por el usuario.
- **EXPECTED:** especificación inferida del modelo comercial, pendiente de confirmación.
- **DISCOVERED:** capacidad detectada, sin prueba de ejecución.
- **COMPATIBLE:** runtime/modelo preparado y compatible según evidencia concreta.
- **REPRODUCED:** inferencia funcional repetida en el dispositivo identificado.
- **MEASURED:** benchmark con protocolo, versiones, configuración y artefactos verificables.
- **VERIFIED:** evidencia revisada y reproducible; no equivale automáticamente a aceptación.

No hay benchmarks físicos LEONES acreditados para este teléfono en este perfil. Ninguna cifra de terceros se atribuirá al dispositivo. Mantener separados rendimiento pico, sostenido, térmico y eficiencia energética.
