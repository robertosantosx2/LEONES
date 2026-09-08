# LEONES RC4 — guía de beta testers

**Estado:** RC4 Beta / candidato de pruebas
**Rama:** `rc4-fitllm-recommender`
**Commit candidato:** `1603f3ed1e0819a942a08bd487b161f84b983435`

## Objetivo

Probar RC4 en equipos reales antes de declarar una versión pública estable.

La beta valida especialmente:

- arranque TUI e idioma;
- detección del estado de la máquina;
- selección múltiple del propósito antes de recomendar;
- feed de evidencia Hugging Face + Artificial Analysis;
- recomendación FitLLM/LLMFit;
- selección humana del modelo;
- gestión de software IA;
- separación estricta `ESTIMATED` / `MEASURED`;
- flujo posterior hacia runtime y medición.

## Regla fundamental

**Una recomendación RC4 nunca es una medición.**

La recomendación debe aparecer como `ESTIMATED` y mantener:

```text
execution_authorized = false
measurement_authorized = false
measured = false
user_choice_required = true
```

El usuario decide qué modelo ejecutar. Solo una ejecución física autorizada y protocolizada puede producir `MEASURED`.

## Qué probar primero

### 1. Arranque

```bash
./leones
```

Debe aparecer primero la selección de idioma. Después debe permanecer visible el centro de control con el menú y sus paneles.

### 2. Estado de la máquina

Comprobar que se muestran, cuando están disponibles:

- CPU;
- RAM;
- disco;
- GPU/VRAM;
- software IA detectado;
- modelos instalados.

No debe confundirse software instalado con software simplemente conocido por LEONES.

### 3. Intención

Entrar en recomendación y seleccionar **uno o varios propósitos**.

Probar al menos:

- `programming`;
- `reasoning`;
- una combinación de ambos.

Una intención vacía debe impedir la recomendación.

### 4. Recomendación

Comprobar que:

- la recomendación se ejecuta después de conocer la intención;
- los candidatos proceden de la intersección respaldada por evidencia;
- como máximo aparecen 3 candidatos;
- los candidatos son `ESTIMATED`;
- no se inicia ningún modelo automáticamente;
- si existen menos de 3 coincidencias aparece `insufficient`, sin rellenar candidatos artificialmente.

La ausencia de Artificial Analysis no debe convertirse en una métrica cero inventada.

### 5. Selección humana

Seleccionar explícitamente un modelo recomendado.

Comprobar que la selección no implica por sí sola ejecución ni medición.

### 6. Gestión de software IA

Probar, cuando el componente esté disponible:

```text
instalación desde cero
        ↓
detección de instalación rota → reparación
        ↓
versión actual → no actualizar innecesariamente
        ↓
versión antigua → actualización real
        ↓
verificación operacional
```

Esta regla es permanente para todo software IA que gestione LEONES, incluido cualquier componente futuro.

## Prueba de ejecución física

La beta puede continuar desde la selección humana hacia el runtime físico cuando el entorno esté preparado.

**No presentar una estimación externa, una recomendación o un resultado de otra máquina como `MEASURED`.**

La cadena canónica es:

```text
USER_INTENT[]
   ↓
HF + Artificial Analysis
   ↓
LEONES evidence feed
   ↓
LLMFit / FitLLM
   ↓
ESTIMATED
   ↓
SELECCIÓN HUMANA
   ↓
STACK
   ↓
RUNTIME
   ↓
AUTORIZACIÓN EXPLÍCITA
   ↓
BENCHMARK
   ↓
MEASURED
```

## JALÓN 2 de referencia

LEONES ya dispone de evidencia física independiente de la recomendación RC4:

```text
runtime: llama.cpp
model: Qwen3 0.6B Instruct AWQ
quantization: Q4_K_M
hardware: CPU / 4 threads
real executions: 5
average: 43.6 tok/s
```

Este resultado sirve como evidencia histórica del protocolo y **no debe presentarse como rendimiento de la máquina del beta tester**.

## Qué informar si algo falla

No editar ni maquillar los resultados.

Recoger:

```bash
git rev-parse HEAD
uname -a
python3 --version
free -h
df -h
```

Y, si procede:

```bash
./scripts/run_capture.sh -- python3 scripts/rc4_fitllm_recommend.py \
  --purpose programming \
  --purpose reasoning
```

Conservar la salida completa y el artefacto generado.

El informe debe incluir como mínimo:

- commit de LEONES;
- sistema operativo;
- CPU;
- RAM;
- GPU/VRAM, si existe;
- propósito(s) seleccionado(s);
- resultado de recomendación;
- modelo seleccionado, si se llegó a seleccionar;
- runtime;
- error o resultado completo;
- `execution_id`, si existe;
- hash SHA-256 del artefacto de evidencia, si existe.

No incluir credenciales, tokens ni datos personales innecesarios.

## Criterio de beta

Un fallo funcional, de interfaz, de instalación, de selección, de autorización o de evidencia es información válida para la beta. No intentar ocultarlo.

La beta termina cuando tengamos suficiente evidencia reproducible para decidir:

```text
RC4 Beta
   ↓
feedback de testers
   ↓
RC4.1 / correcciones
   ↓
CI + validación física
   ↓
RC4 estable
```

## Documentación canónica

- `docs/RC4-ARCHITECTURE.md`
- `docs/TUI_RULES_RC4.md`
- `docs/TUI_USAGE_MODEL_RC4.md`
- `docs/AI_SOFTWARE_INSTALL_CONTRACT_RC4.md`
- `docs/completed/RC4-STRICT-MEASURED-CHAIN-2026-09-07.md`
- `scripts/rc4_release_gate.py`
- `scripts/rc4_fitllm_recommend.py`

> **Beta RC4: probar, observar, conservar evidencia y reportar. No confundir ESTIMATED con MEASURED.**
