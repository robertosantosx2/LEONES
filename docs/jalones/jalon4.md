# JALÓN 4 — Taxonomía y alcance de runtimes físicos

**Estado:** 🟡 EN PREPARACIÓN  
**Base:** `rc1-minimal-script-cleanup`

## 1. Objetivo

Convertir el registro de runtimes en un contrato de selección física: LEONES debe distinguir qué runtimes son apropiados para workstation/local y cuáles para datacenter/serving, antes de intentar ejecutarlos.

JALÓN 4 no mide rendimiento. Define el **alcance operativo** y evita seleccionar un runtime incompatible con el tipo de despliegue o servicio solicitado.

## 2. Taxonomía canónica

### Deployment class

- `workstation`
- `datacenter`

### Serving profile

- `single_user`
- `multi_user`

La combinación de ambos campos forma parte del contrato de selección.

## 3. Registro actual

El registro `runtime-registry.v1.1` contiene 11 runtimes:

- llama.cpp
- FreeToken
- AirLLM
- Ollama
- vLLM
- SGLang
- MLX/MLX-LM
- ExLlama
- OpenVINO
- ONNX Runtime GenAI
- TensorRT-LLM

Cada entrada declara, como mínimo, clase de despliegue, perfil de servicio, modos, arquitecturas, formatos, backends, capacidades, entrypoint, disponibilidad, métrica y requisitos del host.

## 4. Regla de selección

El selector no debe considerar equivalente un runtime local y uno de serving.

Ejemplo canónico:

```text
workstation + single_user
        ↓
llama.cpp / Ollama / FreeToken / AirLLM / ...

 datacenter + multi_user
        ↓
vLLM / SGLang / TensorRT-LLM
```

La clasificación no afirma rendimiento. Solo determina compatibilidad declarativa.

## 5. Regla física

Toda entrada marcada `physical_test_required: true` necesita validación en el host antes de convertirse en evidencia de rendimiento.

El registro puede declarar compatibilidad; no puede convertir esa declaración en medición.

## 6. Separación respecto de JALÓN 3

JALÓN 3 fija cómo medir y conservar evidencia.

JALÓN 4 fija **qué runtime puede entrar legítimamente en el plan de ejecución** según el contexto de despliegue.

```text
JALÓN 3
medir correctamente
       ↓
JALÓN 4
seleccionar correctamente
       ↓
runtime físico
       ↓
evidencia v1.1
```

## 7. Estado de implementación

La taxonomía y el registro ya están implementados. Las pruebas de JALÓN 4 verifican:

- que existen los 11 runtimes canónicos;
- que cada entrada pertenece a la taxonomía declarada;
- que `datacenter + multi_user` acepta vLLM;
- que `datacenter` rechaza Ollama;
- que `workstation + single_user` acepta FreeToken.

## 8. Lo que queda fuera

- benchmark físico de cada runtime;
- comparación de rendimiento entre runtimes;
- instalación automática de runtimes;
- elección de un runtime por velocidad estimada;
- convertir datos de terceros en mediciones locales.

## 9. Criterio de cierre

JALÓN 4 podrá cerrarse cuando el contrato de taxonomía quede integrado de forma verificable en el flujo de selección y exista evidencia automatizada suficiente para impedir combinaciones incompatibles sin depender de intervención manual.

La ejecución física de runtimes seguirá siendo una fase separada y estará sujeta al contrato de medición de JALÓN 3.
